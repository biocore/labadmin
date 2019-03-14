from mock import Mock
from os.path import basename
from mimetypes import guess_type
try:
    from urllib import urlencode
except ImportError:  # py3
    from urllib.parse import urlencode

from future.utils import viewitems

from tornado.testing import AsyncHTTPTestCase, LogTrapTestCase
from knimin.webserver import WebApplication
from knimin.handlers.base import BaseHandler
from knimin import db


class TestHandlerBase(AsyncHTTPTestCase, LogTrapTestCase):
    orig_func = BaseHandler.get_current_user

    def tearDown(self):
        BaseHandler.get_current_user = self.orig_func
        # Remove all access privileges user may hve been given by a test
        db.alter_access_levels('test', [])
        super(TestHandlerBase, self).tearDown()

    def get_app(self):
        self.app = WebApplication()
        return self.app

    def mock_login(self):
        BaseHandler.get_current_user = Mock(return_value='test')

    def mock_login_admin(self):
        db.alter_access_levels('test', [7])
        self.mock_login()

    def get(self, url, data=None, headers=None):
        if isinstance(data, dict):
            data = urlencode(data)
            url = url + '?' + data
        return self.fetch(url, method='GET', headers=headers)

    def post(self, url, data, headers=None):
        if isinstance(data, dict):
            data = urlencode(data, True)
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
        file_info = []
        for f, fp in viewitems(files):
            with open(fp, 'rb') as fin:
                file_info.append((f, basename(fp), fin.read()))
        content_type, body = self.encode_multipart_formdata(data.items(),
                                                            file_info)
        heads = {'content-type': content_type,
                 'content-length': str(len(body))}

        if headers is None:
            headers = heads
        else:
            headers.update(heads)

        return self.fetch(url, method='POST', body=body, headers=headers)

    # https://github.com/bryndin/tornado-flickr-api/blob/master/
    # tornado_flickrapi/multipart.py
    def encode_multipart_formdata(self, fields, files):
        """Encodes form data with files for submission

        Parameters
        ----------
        fields : list of tuple of str
            A sequence of (name, value) elements for regular form fields.
        files : list of tuple of str
            A sequence of (name, filepath, value) elements for data to be
            uploaded as files.
        Returns
        -------
        content_type : str
            content type for the multipart form
        body : httplib.HTTP instance
            Form data, ready for submission as body
        """
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L = []
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            filename = filename.encode("utf8")
            L.append('--' + BOUNDARY)
            L.append(
                'Content-Disposition: form-data; name="%s"; filename="%s"'
                % (key, filename))
            L.append('Content-Type: %s' % self.get_content_type(filename))
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body

    def get_content_type(self, filename):
        return guess_type(filename)[0] or 'application/octet-stream'
