import datetime as dt
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import ga4_report


class TestGA4Report(unittest.TestCase):
    def test_read_only_request_and_result(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
        data = {'type': 'service_account', 'token_uri': ga4_report.TOKEN_URL,
                'client_email': 'example@example.invalid', 'private_key': pem}
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        calls = []
        def fake_open(request, timeout):
            calls.append(request)
            if len(calls) == 1:
                return Response(b'{"access_token":"test-only-token"}')
            return Response(b'{"rows":[{"metricValues":[{"value":"3"},{"value":"4"},{"value":"5"}]}]}')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'key.json'
            path.write_text(json.dumps(data))
            with patch('urllib.request.urlopen', side_effect=fake_open):
                result = ga4_report.read_metrics(path, dt.date(2026, 11, 1), dt.date(2026, 11, 2))
        self.assertEqual(result, (3, 4, 5))
        self.assertEqual(calls[1].get_header('Authorization'), 'Bearer test-only-token')
        self.assertEqual(json.loads(calls[1].data)['metrics'][0]['name'], 'activeUsers')
        self.assertTrue(calls[1].full_url.endswith('/properties/564843315:runReport'))

    def test_rejects_untrusted_token_endpoint_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'key.json'
            path.write_text(json.dumps({'type': 'service_account', 'token_uri': 'https://example.invalid'}))
            with self.assertRaises(ValueError), patch('urllib.request.urlopen') as mocked:
                ga4_report.read_metrics(path, dt.date(2026, 11, 1), dt.date(2026, 11, 2))
            mocked.assert_not_called()

if __name__ == '__main__':
    unittest.main()
