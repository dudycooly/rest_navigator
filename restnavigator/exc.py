from __future__ import print_function


class WileECoyoteException(ValueError):
    '''Raised when a url has a bad scheme'''
    pass


class ZachMorrisException(ValueError):
    '''Raised when a url has too many schemes'''
    pass


class AmbiguousNavigationError(StandardError):
    '''Raised when attempting to dereference a templated Navigator'''
    pass

class HALNavigatorError(Exception):
    """Raised when a response is an error

    Has all of the attributes of a normal HALNavigator. The error body can be
    returned by examining response.body """

    def __init__(self, message, nav=None, status=None, response=None):
        self.nav = nav
        self.response = response
        self.message = message
        self.status = status
        super(HALNavigatorError, self).__init__(message)


class UnexpectedlyNotJSON(TypeError):
    """Raised when a non-json parseable resource is gotten"""

    def __init__(self, msg, response):
        self.msg = msg
        self.response = response

    def __repr__(self):  # pragma: nocover
        return '{.msg}:\n\n\n{.response}'.format(self)
