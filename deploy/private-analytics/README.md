# Private analytics reports

`private_report.py` assembles the daily/weekly aggregate report for VEDAL, Smart Solution, Astor and C3AG. It uses the existing read-only Metrica helper at `/opt/smart-metrika-reports/report.py`, and `ga4_report.py` reads GA4 through a service-account key kept on the server only. Never commit tokens, service-account keys, or recipient IDs.

Astor booking totals are aggregate database records, including possible tests and cancellations. Goal reaches and contact clicks are not confirmed sales or unique leads. Sources for Astor are limited by its sanitised referrer; users who decline web analytics are excluded from web counters. The 18 November 2026 initial GA4 visits include tests, and VEDAL Metrica data before its CSP fix is unreliable.

Production currently runs `astor-private-analytics@.service` through daily and weekly systemd timers. Deploy these two Python files to `/opt/astor-private-analytics/` with root-only permissions, after backing up the existing versions; run without `--send` to check the output. The service gets its private destination from systemd. Idempotency markers prevent duplicate sends; never automatically retry a pending send without checking delivery. Do not move the key into this repository. Validate each site's consent and actual event delivery separately from report output.

Run unit tests: `python3 -m unittest discover -s deploy/private-analytics -p 'test_*.py'` (requires `cryptography`).
