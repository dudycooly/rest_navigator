"""A library to allow navigating rest apis easy."""

from __future__ import print_function
from __future__ import unicode_literals
from restnavigator.exc import UnexpectedlyNotJSON, HALNavigatorError

__version__ = '0.2'

import copy
from weakref import WeakValueDictionary
import functools
import httplib
import re
import json
import urlparse
import webbrowser
import urllib

import requests
import cachecontrol
import unidecode
import uritemplate

from restnavigator import exc, utils


def default_headers():
    """Default headers for HALNavigator"""
    return {'Accept': 'application/hal+json,application/json',
            'User-Agent': 'HALNavigator/{}'.format(__version__)}


def restrict_to(methods=[], templated=None, idempotent=None):
    """A decorator to restrict Navigator functions based on certain criteria

        method_restriction - Navigator methods dependent on certain http methods
        checked for Link's http methods

       templated - template uri is supplied with all parameters before calling

       idempotent - restricting Navigator with Non Idempotent response

    """

    def wrap(fn):
        @functools.wraps(fn)
        def wrapped(self, *args, **qargs):
            if idempotent is not None:
                if self.idempotent != idempotent:
                    raise exc.InvalidOperation(
                        'Cannot {} a non-idempotent resource. '
                        'Maybe you want this object\'s .parent attribute, '
                        'or possibly one of the resources in .links'.format(fn.__name__))

            if self.method_validation:
                allowed_methods = [methods] if isinstance(methods, basestring) else methods
                if allowed_methods is not []:
                    if self.method.lower() not in [method.lower() for method in allowed_methods]:
                        raise exc.InvalidOperation('"{}" is permitted only for link supporting "{}" methods\n'
                                                   'Supported method(s) for {} is "{}"'
                                                   .format(fn.__name__,
                                                           str(methods),
                                                           self.uri or self.template_uri,
                                                           self.method))
            if templated is not None:
                if self.templated:
                    raise exc.AmbiguousNavigationError(
                        'This is a templated Navigator. You must provide values for '
                        'the template parameters before {}ing the resource or else '
                        'explicitly null them out with the syntax: N[:]'.format(fn.__name__))

            return fn(self, *args, **qargs)

        return wrapped

    return wrap


def autofetch(fn):
    """A decorator used by Navigators that fetches the resource if necessary
    prior to calling the function """

    @functools.wraps(fn)
    def wrapped(self, *args, **qargs):
        if self.idempotent and self.response is None:
            self.get(raise_exc=qargs.get('raise_exc', False))
        return fn(self, *args, **qargs)

    return wrapped


class HALNavigator(object):
    """The main navigation entity"""

    # See NonIdempotentResponse for a non-idempotent Navigator
    idempotent = True

    def __init__(self, root,
                 apiname=None,
                 auth=None,
                 headers=None,
                 session=None,
                 cache=False,
                 curie=None):
        self.root = utils.fix_scheme(root)
        self.apiname = utils.namify(root) if apiname is None else apiname
        self.uri = self.root
        self.profile = None
        self.title = None
        self.type = 'application/hal+json'
        self.default_curie = curie
        self.curies = None
        self.session = session or requests.Session()
        if cache:
            if isinstance(cache, cachecontrol.CacheControlAdapter):
                cc = cache
            else:
                cc = cachecontrol.CacheControlAdapter()
            self.session.mount('http://', cc)
            self.session.mount('https://', cc)
        self.session.auth = auth
        self.session.headers.update(default_headers())
        if headers:
            self.session.headers.update(headers)
        self.response = None
        self.state = None
        self.template_uri = None
        self.template_args = None
        self.parameters = None
        self.templated = False
        self._links = None
        # This is the identity map shared by all descendents of this
        # HALNavigator
        self._id_map = WeakValueDictionary({self.root: self})
        self.method = 'GET'
        self.method_validation = False

    @classmethod
    def init_from_hal_json(cls, root_uri, hal_response):
        root_uri = utils.fix_scheme(root_uri)

        try:
            hal_json = json.loads(hal_response)
        except ValueError:
            raise UnexpectedlyNotJSON(
                'Need a valid HAL-JSON to initialise the Navigator', hal_response)

        _halnavigator = cls(root_uri)
        _halnavigator.response = hal_response
        _halnavigator._populate_navigator_properties(hal_json)

        return _halnavigator

    # NonIdempotentResponse
    def _create_non_idempotent_response(self):

        attributes = dict(type=self.response.headers['Content-Type'],
                          response=self.response)

        NIR = self.clone_navigator(attributes)
        NIR.idempotent = False
        NIR.parent = self

        # NonIdempotent Response may have plain text as opposed to hal or json response
        #hence, turn off exception
        NIR._populate_navigator_properties(raise_exc=False)
        # The following attributes from parent does not applicable for
        # NonIdempotentResponse
        NIR.templated = False
        NIR.parameters = None
        NIR.method = 'GET'
        NIR.method_validation = True

        return NIR

    @staticmethod
    def get_state(hal_body):
        """Retrieves HAL special properties from a HAL+JSON response"""
        return {k: v for k, v in hal_body.iteritems()
                if k not in ['_links']}

    @property
    def cacheable(self):
        """Whether this Navigator can be cached"""
        return self.idempotent and not self.templated

    @property
    def relative_uri(self):
        """Returns the link of the current uri compared against the api root.

        This is a good candidate for overriding in a subclass if the api you
        are interacting with uses an unconventional uri layout."""
        if self.uri is None:
            return self.template_uri.replace(self.root, '/')
        else:
            return self.uri.replace(self.root, '/')

    @property
    @autofetch
    def links(self):
        r"""Returns dictionary of navigators from the current resource."""
        return dict(self._links)

    @property
    def status(self):
        if self.response is not None:
            return self.response.status_code, self.response.reason

    def __repr__(self):
        def path_clean(chunk):
            if not chunk:
                return chunk
            if re.match(r'\d+$', chunk):
                return '[{}]'.format(chunk)
            else:
                return '.' + chunk

        byte_arr = self.relative_uri.encode('utf-8')
        unquoted = urllib.unquote(byte_arr).decode('utf-8')
        nice_uri = unidecode.unidecode(unquoted)
        path = ''.join(path_clean(c) for c in nice_uri.split('/'))
        return "{cls}({name}{path})".format(
            cls=type(self).__name__, name=self.apiname, path=path)

    def __eq__(self, other):
        try:
            return self.uri == other.uri and self.apiname == other.apiname
        except Exception:
            return False

    def __ne__(self, other):
        return not self == other

    def __call__(self, raise_exc=True):
        if self.response is None:
            return self.fetch(raise_exc=raise_exc)
        else:
            return self.state.copy()

    def __iter__(self):
        """Part of iteration protocol"""
        yield self
        last = self
        while True:
            current = last.next()
            yield current
            last = current

    @autofetch
    def __nonzero__(self):
        # we override normal exception throwing since the user seems interested
        # in the boolean value
        return bool(self.response)

    def next(self):
        try:
            return self['next']
        except KeyError:
            raise StopIteration()

    @restrict_to(methods=['GET'])
    def __getitem__(self, getitem_args):
        r"""Subselector for a HALNavigator"""

        @autofetch
        def dereference(n, rels):
            """Helper to recursively dereference"""
            if len(rels) == 1:
                ret = n._links[rels[0]]
                if isinstance(ret, list):
                    if len(ret) == 1:
                        return ret[0]
                    else:
                        return [r._make_nav() if r.templated else r for r in ret]
                else:
                    return ret._make_nav() if ret.templated else ret
            else:
                return dereference(n[rels[0]], rels[1:])

        rels, qargs, slug, ellipsis = utils.normalize_getitem_args(
            getitem_args)
        if slug and ellipsis:
            raise SyntaxError("':' and '...' syntax cannot be combined!")
        if rels:
            n = dereference(self, rels)
        else:
            n = self
        if qargs or slug:
            n = n.expand(_keep_templated=ellipsis, **qargs)
        return n

    @autofetch
    def docsfor(self, rel):
        """Obtains the documentation for a link relation. Opens in a webbrowser
        window"""
        prefix, _rel = rel.split(':')
        if prefix in self.curies:
            doc_url = uritemplate.expand(self.curies[prefix], {'rel': _rel})
        else:
            doc_url = rel
        print('opening', doc_url)
        webbrowser.open(doc_url)

    def _make_linked_nav_from(self, body):
        """Creates linked navigators from a HAL response body"""

        def process_links(link):
            """Extract URI from each link to craft the Navigators """
            if isinstance(link, list):
                return utils.LinkList((process_links(lnk), lnk) for lnk in link)
            templated = link.get('templated', False)
            if not templated:
                uri = urlparse.urljoin(self.uri, link['href'])
                template_uri = None
            else:
                uri = None
                template_uri = urlparse.urljoin(self.uri, link['href'])
            method = link.get('method', 'GET')
            cp = self._make_nav(
                uri=uri,
                template_uri=template_uri,
                templated=templated,
                title=link.get('title'),
                type=link.get('type'),
                profile=link.get('profile'),
                method=method,
            )
            if templated:
                cp.uri = None
                cp.parameters = uritemplate.variables(cp.template_uri)
            else:
                cp.template_uri = None
            return cp

        return utils.LinkDict(
            self.default_curie,
            {rel: process_links(links)
             for rel, links in body.get('_links', {}).iteritems()
             if rel not in ['self', 'curies']})

    def _populate_navigator_properties(self, raise_exc=True):
        try:
            body = json.loads(self.response.text)
        except ValueError:
            if raise_exc:
                raise UnexpectedlyNotJSON(
                    "The resource at {.uri} wasn't valid JSON", self.response)
            self.state = {}
            self._links = utils.LinkDict(self.default_curie, {})
            self.method = None
            return

        self.method = body.get('method', 'GET')
        if self.method == 'GET':
            self._links = self._make_linked_nav_from(body)
            self.title = (body.get('_links', {})
                          .get('self', {})
                          .get('title', self.title))
            if 'curies' in body.get('_links', {}):
                curies = body['_links']['curies']
                self.curies = {curie['name']: curie['href'] for curie in curies}
            self.state = self.get_state(body)

    def clone_navigator(self, params):
        """ Creates a shallow copy of the HALNavigator that extra attributes can
        be set on."""
        cp = copy.copy(self)
        cp.idempotent = True
        cp._links = None
        cp.response = None
        cp.state = None
        cp.fetched = False
        for attr, val in params.iteritems():
            if val is not None:
                setattr(cp, attr, val)
        return cp

    def _make_nav(self, **kwargs):
        """
        If the object is already in the identity map, that object is returned
        instead.
        If the object is templated, it doesn't go into the id_map
        """
        if 'uri' in kwargs and kwargs['uri'] in self._id_map:
            return self._id_map[kwargs['uri']]
        cp = self.clone_navigator(kwargs)
        if cp.cacheable:
            self._id_map[cp.uri] = cp
        return cp

    def authenticate(self, auth):
        """Allows setting authentication for future requests to the api"""
        self.session.auth = auth

    def expand(self, _keep_templated=False, **kwargs):
        """Expand template args in a templated Navigator.

        if :_keep_templated: is True, the resulting Navigator can be further
        expanded. A Navigator created this way is not part of the id map.
        """

        if not self.templated:
            raise TypeError(
                "This Navigator isn't templated! You can't expand it.")

        for k, v in kwargs.iteritems():
            if v == 0:
                kwargs[k] = '0'  # uritemplate expands 0's to empty string

        if self.template_args is not None:
            kwargs.update(self.template_args)
        cp = self._make_nav(uri=uritemplate.expand(self.template_uri, kwargs),
                            templated=_keep_templated)
        if not _keep_templated:
            cp.template_uri = None
            cp.template_args = None
        else:
            cp.template_args = kwargs

        return cp

    def get_http_response(self,
                          http_method_fn,
                          body=None,
                          raise_exc=True,
                          content_type='application/json',
                          json_cls=None,
                          headers=None):
        """
            Fetches HTTP response using http method (POST or DELETE of requests.Session)
        resource. Returns a new HALNavigator representing that resource.

        `body` may either be a string or a dictionary which will be serialized
            as json
        `content_type` may be modified if necessary
        `json_cls` is a JSONEncoder to use rather than the standard
        `headers` are additional headers to send in the request"""

        if isinstance(body, dict):
            body = json.dumps(body, cls=json_cls, separators=(',', ':'))
        headers = {} if headers is None else headers
        headers['Content-Type'] = content_type
        self.response = response = http_method_fn(
            self.uri,
            data=body,
            headers=headers,
            allow_redirects=False)
        if raise_exc and not response:
            raise HALNavigatorError(
                message=response.text,
                status=response.status_code,
                nav=self,
                response=response,
            )
        return response


    def create_navigator_or_non_idempotent_resp(self, method):

        if self.response.status_code in (httplib.CREATED,  # Applicable for POST
                                         httplib.FOUND,  # RFC says, redirect should not be allowed other than GET/HEAD
                                         httplib.SEE_OTHER,
                                         httplib.NO_CONTENT) and 'Location' in self.response.headers:
            return self._make_nav(uri=self.response.headers['Location'])

        elif self.response.status_code == httplib.OK:
            # Only Status expected to return a HAL Response

            if method.upper() in ['POST', 'DELETE']:
                return self._create_non_idempotent_response()
            elif method.upper() == 'GET':
                return self._populate_navigator_properties()
        else:
            '''
                Expected hits:
                CREATED or Redirection without Locaiton,
                NO_CONTENT = 204
                ACCEPTED = 202 and
                4xx, 5xx errors.

                If something else, then requires rework

                '''
            return self.status

    def _fetch_hal_and_create_resource(self, http_method_fn,
                                       body=None,
                                       raise_exc=True,
                                       content_type='application/json',
                                       json_cls=None,
                                       headers=None, ):

        self.get_http_response(http_method_fn,
                               body,
                               raise_exc,
                               content_type,
                               json_cls,
                               headers)

        return self.create_navigator_or_non_idempotent_resp(http_method_fn.__name__)


    @restrict_to(methods='GET', templated=True, idempotent=True)
    def get(self, raise_exc=True):
        """Like __call__, but doesn't cache, always makes the request"""
        # self._fetch_hal_and_create_resource(self.session.get)
        self.get_http_response(self.session.get, raise_exc=raise_exc)
        self._populate_navigator_properties(raise_exc)
        return self.state

    fetch = get

    @restrict_to(methods='POST', templated=True)
    def create(self, *args, **kwargs):
        """Performs an HTTP POST to the server, to create source(s) """
        return self._fetch_hal_and_create_resource(self.session.post, *args, **kwargs)

    post = create

    @restrict_to(methods='DELETE', templated=True)
    def delete(self, *args, **kwargs):
        """Performs an HTTP DELETE to the server, to delete resource(s)."""
        return self._fetch_hal_and_create_resource(self.session.delete, *args, **kwargs)