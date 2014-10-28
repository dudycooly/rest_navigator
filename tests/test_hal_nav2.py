'''Refactored tests from test_hal_nav.py'''

import json

import httpretty
import pytest

import restnavigator.halnav as HN


def uri_of(doc):
    return doc['_links']['self']['href']


def register_hal_page(doc, **kwargs):
    httpretty.HTTPretty.register_uri(
        kwargs.get('method', 'GET'),
        body=json.dumps(doc),
        uri=doc['_links']['self']['href'],
        **kwargs
    )


@pytest.fixture
def http(request):
    httpretty.HTTPretty.enable()
    def finalizer():
        httpretty.HTTPretty.disable()
        httpretty.HTTPretty.reset()
    request.addfinalizer(finalizer)
    return httpretty.HTTPretty

@pytest.fixture
def index_uri():
    return 'http://example.com/api/'


@pytest.fixture
def N(index_uri):
    '''A basic HALNavigator with the index_uri as root'''
    return HN.HALNavigator(index_uri)


class TestEmbedded:
    '''tests for embedded document features'''

    def page(name, number):
        '''returns a generic resource page'''
        return {
            '_links': {
                'self': {
                    'href': index_uri() + name + '/' + str(number),
                    'name': name + str(number),
                },
                'next': {'href': index_uri() + name + '/' + str(number + 1)},
            },
            name + '_data': name + ' data here',
            'number': number,
        }

    @pytest.fixture
    def posts(self, http):
        '''Posts are both linked and embedded'''
        _posts = [self.page('post', x) for x in xrange(3)]
        for post in _posts:
            register_hal_page(post)
        return _posts

    @pytest.fixture
    def comments(self):
        '''Comments are embedded only and have no self link'''
        comments = [self.page('comments', x) for x in xrange(3)]
        for comment in comments:
            del comment['_links']['self']
        return comments

    @pytest.fixture
    def index(self, index_uri, comments, posts, http):
        doc = {
            '_links': {
                'curies': [{
                    'name': 'xx',
                    'href': index_uri + 'rels/{rel}',
                    'templated': True,
                }],
                'self': {'href': index_uri},
                'first': posts[0]['_links']['self'],
                'xx:second': posts[1]['_links']['self'],
                'xx:posts': [post['_links']['self'] for post in posts]
            },
            'data': 'Some data here',
            '_embedded': {
                'xx:posts': posts,
                'xx:comments': comments,
            }
        }
        register_hal_page(doc)
        return doc

    def test_only_idempotent(self, N, index):
        assert not N['xx:comments'][0].idempotent

    def test_length_accurate(self, N, index, comments):
        assert len(N['xx:comments']) == len(comments)

    def test_links_and_embedded(self, N, index):
        assert 'xx:comments' in N
        assert 'xx:comments' not in N.links
        assert 'xx:comments' in N.embedded
        assert 'xx:posts' in N
        assert 'xx:posts' in N.links
        assert 'xx:posts' in N.embedded

        