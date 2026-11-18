"""Read aggregate GA4 metrics with a service-account key, without logging secrets."""
import base64
import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

TOKEN_URL = 'https://oauth2.googleapis.com/token'
PROPERTY_ID = '564843315'
SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=')


def _post_json(url, body, headers=None):
    request = urllib.request.Request(url, data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', **(headers or {})})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def read_metrics(key_file, start, end, property_id=PROPERTY_ID, details=False):
    if not isinstance(start, dt.date) or not isinstance(end, dt.date) or start > end:
        raise ValueError('Invalid reporting interval')
    credential = json.loads(Path(key_file).read_text())
    if credential.get('type') != 'service_account' or credential.get('token_uri') != TOKEN_URL:
        raise ValueError('Unexpected service account credential')
    now = int(time.time())
    header = _b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}, separators=(',', ':')).encode())
    claims = _b64(json.dumps({'iss': credential['client_email'], 'scope': SCOPE,
        'aud': TOKEN_URL, 'iat': now, 'exp': now + 300}, separators=(',', ':')).encode())
    unsigned = header + b'.' + claims
    key = serialization.load_pem_private_key(credential['private_key'].encode(), password=None)
    signature = key.sign(unsigned, padding.PKCS1v15(), hashes.SHA256())
    assertion = (unsigned + b'.' + _b64(signature)).decode('ascii')
    req = urllib.request.Request(TOKEN_URL, data=urllib.parse.urlencode({
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': assertion}).encode(), headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=20) as response:
        token = json.load(response)['access_token']
    if not str(property_id).isdigit():
        raise ValueError('Invalid property ID')
    result = _post_json(f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport', {
        'dateRanges': [{'startDate': start.isoformat(), 'endDate': end.isoformat()}],
        'metrics': [{'name': 'activeUsers'}, {'name': 'sessions'}, {'name': 'screenPageViews'}],
    }, {'Authorization': 'Bearer ' + token})
    rows = result.get('rows', [])
    values = rows[0]['metricValues'] if rows else []
    if values and len(values) != 3:
        raise ValueError('Unexpected GA4 response')
    counts = tuple(int(item['value']) for item in values) if values else (0, 0, 0)
    if not details:
        return counts
    # Event names only; never request event parameters, user IDs or form contents.
    try:
        events = _post_json(f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport', {
            'dateRanges': [{'startDate': start.isoformat(), 'endDate': end.isoformat()}],
            'dimensions': [{'name': 'eventName'}], 'metrics': [{'name': 'eventCount'}],
            'limit': '30',
        }, {'Authorization': 'Bearer ' + token})
        import re
        automatic = {'page_view', 'session_start', 'first_visit', 'user_engagement', 'scroll', 'click'}
        event_rows = []
        for row in events.get('rows', []):
            name = row['dimensionValues'][0]['value']
            if name not in automatic and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,39}', name):
                event_rows.append((name, int(row['metricValues'][0]['value'])))
        sources = _post_json(f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport', {
            'dateRanges': [{'startDate': start.isoformat(), 'endDate': end.isoformat()}],
            'dimensions': [{'name': 'sessionSourceMedium'}], 'metrics': [{'name': 'sessions'}], 'limit': '10',
        }, {'Authorization': 'Bearer ' + token})
        source_rows = []
        for row in sources.get('rows', []):
            name = row['dimensionValues'][0]['value']
            if len(name) <= 60 and re.fullmatch(r'[A-Za-z0-9_ .()/+-]+', name):
                source_rows.append((name, int(row['metricValues'][0]['value'])))
        return counts, sorted(event_rows, key=lambda x: (-x[1], x[0]))[:3], sorted(source_rows, key=lambda x: (-x[1], x[0]))[:3]
    except Exception:
        return counts, None, None
