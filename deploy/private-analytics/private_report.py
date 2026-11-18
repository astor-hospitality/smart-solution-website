#!/usr/bin/env python3
"""Private, aggregate-only report; never print tokens, chat IDs, or response bodies."""
import argparse
import datetime as dt
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path('/opt/smart-metrika-reports')
STATE = Path('/var/lib/astor-private-analytics')
GATEWAY = 'https://astorapp-telegram-backup.michael-poedinenko-mxr.workers.dev'
EXPECTED_BOT = 8662797750
SITES = [('VEDAL', 112490942), ('Smart Solution', 113756904), ('Astor Mini App', 113931017), ('C3AG', 114300351)]
spec = importlib.util.spec_from_file_location('existing_metrika_report', ROOT / 'report.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

SAFE_PAGES = {'/', '/about', '/about-us', '/services', '/service', '/contacts', '/contact',
              '/catalog', '/products', '/production', '/news', '/podcast', '/cases', '/projects',
              '/team', '/pricing', '/events', '/privacy', '/ru', '/en', '/ai', '/reels',
              '/reclama', '/film', '/wedding', '/other'}

def safe_page(value):
    """Never send arbitrary paths, parameters or possible personal data to Telegram."""
    path = urllib.parse.urlsplit(value).path.rstrip('/') or '/'
    return path if path in SAFE_PAGES else 'Другие страницы / экраны'

def safe_source(value):
    value = str(value or '').strip()
    if not value or value.lower() in ('not set', '(not set)', 'не определено'):
        return ''
    # Avoid sending arbitrary referral URLs, identifiers, contacts, or query parameters.
    if len(value) > 45 or not re.fullmatch(r'[\w .А-Яа-яЁё+()-]+', value):
        return 'другие источники'
    return value

def breakdown(counter, start, end, dimensions, metric, page=False):
    params = {'ids': counter, 'date1': start.isoformat(), 'date2': end.isoformat(),
              'dimensions': dimensions, 'metrics': metric, 'accuracy': 'full',
              'timezone': '+05:00', 'lang': 'ru', 'limit': 30, 'include_undefined': 'true'}
    data = source.metrika('/stat/v1/data?' + urllib.parse.urlencode(params))
    rows = data.get('data')
    if not isinstance(rows, list):
        raise ValueError('Incomplete breakdown')
    totals = {}
    for row in rows:
        dims = row.get('dimensions', [])
        if not dims or not row.get('metrics'):
            continue
        if page:
            label = safe_page(dims[0].get('name', ''))
        else:
            names = [safe_source(d.get('name', '')) for d in dims]
            label = ' / '.join(dict.fromkeys(x for x in names if x)) or 'Источник не определён'
        totals[label] = totals.get(label, 0) + int(row['metrics'][0])
    return sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:3], bool(data.get('sampled'))

def detail_lines(counter, start, end):
    lines = []
    for heading, dim, metric, is_page, noun in [
        ('Источники визитов', 'ym:s:lastTrafficSource,ym:s:lastSourceEngine', 'ym:s:visits', False, 'виз.'),
        ('Популярные страницы', 'ym:pv:URLPath', 'ym:pv:pageviews', True, 'просм.')]:
        try:
            rows, sampled = breakdown(counter, start, end, dim, metric, page=is_page)
            lines.append(heading + ': ' + ('; '.join(f'{name} — {count} {noun}' for name, count in rows) if rows else 'нет данных'))
            if sampled:
                lines.append('Детализация с семплированием.')
        except Exception:
            lines.append(heading + ': данные временно недоступны (не ноль).')
    return lines

def vedal_counter_warning():
    try:
        req = urllib.request.Request('https://vedal-med.ru/', method='HEAD')
        with urllib.request.urlopen(req, timeout=8) as response:
            policy = response.headers.get('Content-Security-Policy', '')
        scripts = next((part for part in policy.split(';') if part.strip().startswith('script-src ')), '')
        if policy and scripts and 'https://mc.yandex.ru' not in scripts:
            return 'Внимание: CSP сайта блокирует скрипт Метрики; нули не доказывают отсутствие трафика.'
    except Exception:
        return 'Доступность счётчика на сайте не проверена.'
    return None

def astor_application_counts(start, end):
    # Aggregate operational records only. No names, contact details or message contents.
    end_exclusive = end + dt.timedelta(days=1)
    start_utc = dt.datetime.combine(start, dt.time.min, ZoneInfo('Asia/Yekaterinburg')).isoformat()
    end_utc = dt.datetime.combine(end_exclusive, dt.time.min, ZoneInfo('Asia/Yekaterinburg')).isoformat()
    query = ("SELECT 'reservations', count(*) FROM reservations WHERE created_at >= "
             f"TIMESTAMPTZ '{start_utc}' AND created_at < TIMESTAMPTZ '{end_utc}' "
             "UNION ALL SELECT 'place_requests', count(*) FROM place_requests WHERE created_at >= "
             f"TIMESTAMPTZ '{start_utc}' AND created_at < TIMESTAMPTZ '{end_utc}'")
    output = subprocess.check_output(['docker', 'exec', 'astor-postgres', 'psql', '-X', '-U', 'astor',
        '-d', 'astor', '-A', '-t', '-F', '|', '-v', 'ON_ERROR_STOP=1', '-c', query], timeout=12, text=True)
    counts = dict(line.split('|', 1) for line in output.splitlines() if '|' in line)
    if set(counts) != {'reservations', 'place_requests'}:
        raise ValueError('Incomplete application counts')
    return int(counts['reservations']), int(counts['place_requests'])

def send_api(method, params):
    token = source.read_env('/opt/astor-platform/astor/.env')['TELEGRAM_BOT_TOKEN']
    req = urllib.request.Request(f'{GATEWAY}/bot{token}/{method}',
        data=urllib.parse.urlencode(params).encode(), headers={'User-Agent': 'AstorMetrics/1.0'})
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.load(response)
    if not result.get('ok'):
        raise RuntimeError('Telegram request rejected')
    return result['result']

def report(mode, today):
    start, end = source.period(mode, today)
    days = (end - start).days + 1
    result = [f'📊 {"Еженедельная" if mode == "weekly" else "Ежедневная"} сводка · Яндекс и Google',
              f'{start:%d.%m.%Y} – {end:%d.%m.%Y} · Екатеринбург', '']
    key_path = Path('/opt/astor-private-analytics/ga4-service-account.json')
    ga_properties = {112490942: '564937436', 113756904: '564994217',
                     113931017: '564843315', 114300351: '564802138'}
    for title, counter in SITES:
        result.append(f'🌐 {title}')
        if counter == 113931017:
            try:
                reservations, requests = astor_application_counts(start, end)
                result.extend([f'Заявки в базе Astor: бронирования — {reservations}; запросы в другие места — {requests}.',
                               'Созданные заявки, включая возможные тесты и отмены; не подтверждённые продажи.'])
            except Exception:
                result.append('Заявки в базе Astor: данные недоступны, это не ноль.')
        result.append('Яндекс Метрика:')
        try:
            goals_available = True
            try:
                definitions = source.metrika(f'/management/v1/counter/{counter}/goals')['goals']
                wanted = ('Заявка:', 'Ведалина:', 'Контакт:', 'Форма: открытие Telegram',
                          'Клик:', 'Скачивание документа', 'Помощник:', 'Услуги:')
                goals = [(g['id'], g['name']) for g in definitions if g.get('name', '').startswith(wanted)]
            except Exception:
                goals = []
                goals_available = False
            current, meta = source.stats(counter, goals, start, end)
            try:
                previous, _ = source.stats(counter, [], start - dt.timedelta(days=days), end - dt.timedelta(days=days))
                comparison = ' · ' + source.change(current[1], previous[1])
            except Exception:
                comparison = ' · сравнение временно недоступно'
            result.extend([f'Посетители: {int(current[1])}{comparison}',
                           f'Визиты: {int(current[0])} · просмотры: {int(current[2])}',
                           f'Отказы: {current[3]:.1f}%'])
            result.extend(detail_lines(counter, start, end))
            if counter == 113931017:
                result.append('Важно: источник Astor очищается приложением; «прямые заходы» не подтверждают реальный канал.')
            if goals:
                lead_prefix = ('Заявка:', 'Ведалина: создать заявку', 'Контакт:', 'Форма: открытие Telegram')
                lead_goals = [(name, int(current[6+i])) for i, (_, name) in enumerate(goals) if name.startswith(lead_prefix)]
                interest_goals = [(name, int(current[6+i])) for i, (_, name) in enumerate(goals) if not name.startswith(lead_prefix) and current[6+i] > 0]
                if lead_goals:
                    result.append('Цели контакта (не подтверждённые заявки):')
                    for name, value in lead_goals:
                        if counter in (113931017, 114300351) and end < dt.date(2026, 11, 18):
                            result.append(f'• {name}: не собиралось в этот период')
                        else:
                            result.append(f'• {name}: {value}')
                else:
                    result.append('Цели заявок не найдены; число заявок не определено.')
                result.append('Интерес — действия: ' + ('; '.join(f'{name} — {value}' for name, value in interest_goals[:4]) if interest_goals else 'не зафиксированы'))
            elif not goals_available:
                result.append('Цели: список временно недоступен (не ноль).')
            else:
                result.append('Цели заявок не найдены; число заявок не определено.')
            if meta.get('sampled'):
                result.append('Данные с семплированием.')
            if counter == 112490942:
                if start < dt.date(2026, 11, 18):
                    result.append('До 18.11 CSP блокировал Метрику: исторические нули ненадёжны.')
                warning = vedal_counter_warning()
                if warning:
                    result.append(warning)
            if counter == 113931017:
                result.append('Только посетители, разрешившие аналитику; не все пользователи Astor.')
                result.append('Цели созданы 18.11; приём событий пока не проверен на реальной заявке.')
            if counter == 114300351:
                result.append('Новый счётчик; только посетители, разрешившие аналитику.')
                result.append('Цели контактов созданы 18.11; фактическая передача событий ещё не проверена.')
        except Exception as error:
            status = getattr(error, 'code', None)
            result.append(f'Данные недоступны{f" (HTTP {status})" if status else ""}; это не ноль.')
        result.append('Google Analytics:')
        if counter not in ga_properties or not key_path.is_file():
            result.append('Не подключён к этому отчёту; показатели неизвестны.')
        elif counter in (112490942, 113756904) and end < dt.date(2026, 11, 18):
            result.append('До 18.11 Google Analytics не был подключён; данные за период отсутствуют.')
        else:
            try:
                from ga4_report import read_metrics
                (users, sessions, views), events, ga_sources = read_metrics(key_path, start, end, ga_properties[counter], details=True)
                result.extend([f'Активные пользователи: {users} · сеансы: {sessions} · просмотры: {views}',
                               'Источники сеансов: ' + ('данные недоступны' if ga_sources is None else '; '.join(f'{name} — {count}' for name, count in ga_sources) if ga_sources else 'нет данных'),
                               'Другие события: ' + ('данные недоступны' if events is None else '; '.join(f'{name} — {count}' for name, count in events) if events else 'нет зарегистрированных')])
                if counter in (112490942, 113756904):
                    result.append('Сбор с 18.11 и только с согласия; возможны тестовые визиты.')
            except Exception as error:
                status = getattr(error, 'code', None)
                result.append(f'Данные недоступны{f" (HTTP {status})" if status else ""}; это не ноль.')
        result.append('')
    result += ['', 'Источники — последний переход; страницы — просмотры, не доказательство интереса.',
               'Цели — действия, не уникальные лиды и не продажи. Контакты посетителей счётчики не раскрывают.',
               'Яндекс и Google не суммируются. Для Astor и C3AG — только разрешившие аналитику. #аналитика']
    return '\n'.join(result), start, end

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['daily', 'weekly'], default='daily')
    parser.add_argument('--send', action='store_true')
    parser.add_argument('--update', action='store_true', help='Send one corrected report for the same period')
    args = parser.parse_args()
    text, start, end = report(args.mode, dt.datetime.now(ZoneInfo('Asia/Yekaterinburg')).date())
    if not args.send:
        print(text)
        return
    chat_id = int(os.environ['ASTOR_PRIVATE_REPORT_CHAT_ID'])
    bot = send_api('getMe', {})
    chat = send_api('getChat', {'chat_id': chat_id})
    if bot.get('id') != EXPECTED_BOT or chat.get('id') != chat_id or chat.get('type') != 'private':
        raise RuntimeError('Destination or bot guard failed')
    STATE.mkdir(mode=0o700, exist_ok=True)
    with (STATE / 'send.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = STATE / f'{args.mode}-{start}-{end}{"-update-v4" if args.update else ""}.json'
        if marker.exists():
            status = json.loads(marker.read_text()).get('status')
            if status == 'sent':
                print('Already sent; skipped')
                return
            raise RuntimeError('Prior send is uncertain; inspect before retry')
        marker.write_text(json.dumps({'status': 'pending'}))
        ids = []
        for part in source.chunks(text):
            sent = send_api('sendMessage', {'chat_id': chat_id, 'text': part, 'disable_web_page_preview': 'true'})
            ids.append(sent['message_id'])
            marker.write_text(json.dumps({'status': 'pending', 'message_ids': ids}))
        marker.write_text(json.dumps({'status': 'sent', 'message_ids': ids}))
        print('Private report sent; Telegram accepted message')

if __name__ == '__main__':
    os.umask(0o077)
    try:
        main()
    except Exception as error:
        print('Report failed:', type(error).__name__, getattr(error, 'code', ''), file=sys.stderr)
        sys.exit(1)
