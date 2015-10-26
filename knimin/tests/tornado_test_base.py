from mock import Mock
try:
    from urllib import urlencode
except ImportError:  # py3
    from urllib.parse import urlencode

from tornado.testing import AsyncHTTPTestCase, LogTrapTestCase
from knimin.webserver import WebApplication
from knimin.handlers.base import BaseHandler


class TestHandlerBase(AsyncHTTPTestCase, LogTrapTestCase):
    orig_func = BaseHandler.get_current_user

    def tearDown(self):
        BaseHandler.get_current_user = self.orig_func
        super(TestHandlerBase, self).tearDown()

    def get_app(self):
        self.app = WebApplication()
        return self.app

    def mock_login(self):
        BaseHandler.get_current_user = Mock(return_value='test')

    def get(self, url, data=None, headers=None):
        if isinstance(data, dict):
                data = urlencode(data)
                url = url + '?' + data
        return self.fetch(url, method='GET', headers=headers)

    def post(self, url, data, headers=None):
        if isinstance(data, dict):
                data = urlencode(data)
        return self.fetch(url, method='POST', body=data, headers=headers)
