from tornado.web import HTTPError

from knimin import db


def set_access(access_levels=['Admin']):
    """Decorator that resricts access to specific user group(s)

    Parameters
    ----------
    access_levels : list of str
        Access levels to allow access to. Default Admin

    Raises
    ------
    HTTPError
        403 error if user does not have access to the page
    """
    def class_modifier(cls):
        class DecoratedClass(cls):
            _access_levels = access_levels

            def _has_access(self):
                # If no user, let the authenticated decorator take over
                if self.current_user is None:
                    return
                # Base level access is given to everyone
                if self._access_levels[0] == 'Base':
                    return
                if not db.has_access(self.current_user, self._access_levels):
                    raise HTTPError(403, 'User %s does not have access level '
                                    '%s' % (self.current_user,
                                            ', '.join(self._access_levels)))

            # Decorate the get post, put, and delete methods to restrict
            # access automatically using decorator
            def get(self):
                self._has_access()
                super(DecoratedClass, self).get()

            def post(self):
                self._has_access()
                super(DecoratedClass, self).post()

            def put(self):
                self._has_access()
                super(DecoratedClass, self).put()

            def delete(self):
                self._has_access()
                super(DecoratedClass, self).delete()

        return DecoratedClass
    return class_modifier
