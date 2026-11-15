"""Read-only deployment checks. Run: python3 scripts/check_live.py."""
import argparse
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import urlopen


def fetch(url):
    with urlopen(url, timeout=15) as response:
        return response.read().decode('utf-8')


def check(api, web):
    if json.loads(fetch(api + '/health')) != {'status': 'ok'}:
        raise ValueError('API is not healthy')
    print('PASS: API and database health')
    paths = json.loads(fetch(api + '/openapi.json'))['paths']
    required = ['/owner/schedule', '/owner/manual-bookings', '/owner/overview',
                '/owner/blocks', '/owner/payments/{booking_id}', '/admin/attention',
                '/admin/people', '/admin/activity', '/admin/notifications', '/admin/bookings/{booking_id}']
    if not all(path in paths for path in required):
        raise ValueError('Owner/admin API endpoints are missing')
    for path in ('/owner/overview', '/admin/venues', '/admin/attention', '/admin/people',
                 '/admin/activity', '/admin/notifications', '/admin/bookings/1'):
        try:
            fetch(api + path)
        except HTTPError as error:
            if error.code == 401:
                continue
            raise ValueError('Unexpected authentication response') from None
        raise ValueError('Protected endpoint accepted an unauthenticated request')
    print('PASS: owner/admin endpoints present; owner/admin authentication enforced')
    html = fetch(web + '/')
    scripts = re.findall(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\']', html)
    bundles = [path for path in scripts if path.startswith('/assets/') and path.endswith('.js')]
    if not bundles:
        raise ValueError('Frontend JavaScript bundle is missing')
    bundle = '\n'.join(fetch(urljoin(web + '/', path)) for path in bundles)
    if not all(value in bundle for value in (api, '/owner/schedule', '/owner/manual-bookings', '/admin/attention', '/admin/people', '/admin/activity')):
        raise ValueError('Frontend owner/admin features or API origin do not match')
    print('PASS: frontend assets, owner/admin features and API origin')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', default='https://maydon-production-ba2c.up.railway.app')
    parser.add_argument('--web', default='https://maydon-web-production-3612.up.railway.app')
    args = parser.parse_args()
    try:
        check(args.api.rstrip('/'), args.web.rstrip('/'))
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
        # Avoid printing response bodies or connection details into deployment logs.
        print('FAIL: deployment check failed; inspect service health, authentication and assets.', file=sys.stderr)
        sys.exit(1)
