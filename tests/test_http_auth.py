import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from meetingbot_http import dispatch_request, NoRedirect

class ClientTests(unittest.TestCase):
    def test_auth_before_network(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError): dispatch_request('http://127.0.0.1:3001/health')
        with patch.dict(os.environ, {'MEETINGBOT_DISPATCH_TOKEN': 'synthetic-fixture-'*3}, clear=True):
            req = dispatch_request('http://127.0.0.1:3001/health')
            self.assertEqual(req.get_header('Authorization'), 'Bearer '+'synthetic-fixture-'*3)
            with self.assertRaises(ValueError): dispatch_request('http://example.invalid/health')
            with self.assertRaises(ValueError): NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.invalid')

if __name__ == '__main__': unittest.main()
