"""Run with uv run --with terminado==0.18.1 python -m unittest discover -s tests."""
import base64
import importlib.util
import unittest
from unittest.mock import Mock

if importlib.util.find_spec('terminado') is None:
    raise unittest.SkipTest('terminal tests require terminado')

from tornado.testing import AsyncHTTPTestCase

from _term import make_app


class TerminalAccessTests(AsyncHTTPTestCase):
    def get_app(self):
        credentials = base64.b64encode(b'wserv:test-password')
        self.auth = b'Basic ' + credentials
        self.manager = Mock()
        return make_app(self.manager, credentials, None)

    def test_page_requires_login(self):
        response = self.fetch('/')
        self.assertEqual(response.code, 401)
        self.assertIn('Basic', response.headers['WWW-Authenticate'])
        self.assertEqual(self.fetch('/', headers={'Authorization': self.auth}).code, 200)

    def test_socket_requires_login_before_upgrade(self):
        headers = {'Connection': 'Upgrade', 'Upgrade': 'websocket',
                   'Sec-WebSocket-Version': '13', 'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ=='}
        self.assertEqual(self.fetch('/ws', headers=headers).code, 401)
        self.manager.get_terminal.assert_not_called()


class LoopbackTerminalTests(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(Mock(), None, None)

    def test_loopback_page_and_websocket_pass_login(self):
        self.assertEqual(self.fetch('/').code, 200)
        # The socket proceeds to the upgrade check.
        self.assertEqual(self.fetch('/ws').code, 400)

    def test_foreign_host_is_rejected_before_opening_shell(self):
        for route in ('/', '/ws'):
            self.assertEqual(self.fetch(route, headers={'Host': 'example.org'}).code, 403)
