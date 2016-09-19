from unittest import main

from tornado.escape import url_escape

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestAGNewKitDLHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_new_kit/download/')
        self.assertEqual(response.code, 405)  # Method Not Allowed

    def test_post(self):
        print("AGNewKitDLHandler -> post: empty")


class TestAGNewKitHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_new_kit/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/ag_new_kit/')))

    def test_get(self):
        print("AGNewKitHandler -> get: empty")

    def test_post(self):
        print("AGNewKitHandler -> post: empty")


if __name__ == "__main__":
    main()
