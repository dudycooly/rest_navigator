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

class HALJSONParseError(StandardError):

    '''Raised when attempting to retrieve a property (link, state, embedded) from hal json supplied'''
    pass
