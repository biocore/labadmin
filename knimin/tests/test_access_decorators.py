from unittest import main

from tornado.web import HTTPError

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin.handlers.access_decorators import set_access


@set_access(['Base'])
class AccessTests(TestHandlerBase):
    def get(self):
        # overloading as TestHandlerBase redefines signature of get
        pass

    def post(self):
        # overloading as TestHandlerBase redefines signature of post
        pass

    def put(self):
        # TestHandlerBase does not define
        pass

    def delete(self):
        # TestHandlerBase does not define
        pass

    def test_has_access(self):
        self.current_user = 'test'

        self.get()
        self.post()
        self.put()
        self.delete()

    def test_does_not_exist(self):
        self.current_user = 'does not exist'

        with self.assertRaises(HTTPError):
            self.get()
        with self.assertRaises(HTTPError):
            self.post()
        with self.assertRaises(HTTPError):
            self.put()
        with self.assertRaises(HTTPError):
            self.delete()


@set_access(['Admin'])
class UnknownUserBaseTests(TestHandlerBase):
    def get(self):
        # overloading as TestHandlerBase redefines signature of get
        pass

    def post(self):
        # overloading as TestHandlerBase redefines signature of post
        pass

    def put(self):
        # TestHandlerBase does not define
        pass

    def delete(self):
        # TestHandlerBase does not define
        pass

    def test_needs_admin(self):
        self.current_user = 'test'

        with self.assertRaises(HTTPError):
            self.get()
        with self.assertRaises(HTTPError):
            self.post()
        with self.assertRaises(HTTPError):
            self.put()
        with self.assertRaises(HTTPError):
            self.delete()


if __name__ == '__main__':
    main()
