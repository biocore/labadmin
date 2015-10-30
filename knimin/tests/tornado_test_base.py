from mock import Mock
from os.path import basename
try:
    from urllib import urlencode
except ImportError:  # py3
    from urllib.parse import urlencode

from requests_toolbelt import MultipartEncoder

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

    def multipart_post(self, url, data, files, headers=None):
        """Handles file upload testing

        Parameters
        ----------
        url : str
            URL path (minus the base URL) to post to
        data : dict
            Dictionary of non-file info in the form {name: value, ...}
        files : dict
            Dictionary of file info in the form {name: filepath, ...}
        headers : dict, optional
            Any headers that need to be added

        Returns
        -------
        request object
            The result of the post command
        """
        fields = {f: (basename(fp), open(fp, 'rb'), 'text/plain')
                  for f, fp in files.items()}
        fields.update(data)
        m = MultipartEncoder(fields=fields)
        if headers is None:
            headers = {'Content-Type': m.content_type}
        else:
            headers.update({'Content-Type': m.content_type})

        return self.fetch(url, data=m, headers=headers)
