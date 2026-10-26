"""Authenticated HTTP client; importing this module never starts the recorder."""
import os
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Backend redirects are not permitted')


def dispatch_request(url, *, data=None, method='GET'):
    token = os.environ.get('MEETINGBOT_DISPATCH_TOKEN', '')
    if len(token) < 32:
        raise ValueError('MEETINGBOT_DISPATCH_TOKEN must be configured (at least 32 characters)')
    parsed = urllib.parse.urlsplit(url)
    if parsed.username or parsed.password or not (parsed.scheme == 'https' or (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost', '::1'))):
        raise ValueError('Backend requires HTTPS or loopback HTTP')
    return urllib.request.Request(url, data=data, method=method, headers={
        'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+token})


def open_dispatch(request, timeout):
    return urllib.request.build_opener(NoRedirect).open(request, timeout=timeout)
