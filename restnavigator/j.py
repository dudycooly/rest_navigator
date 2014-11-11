from restnavigator import HALNavigator
import simplejson

hal_json = {'_links': {'curies': [{'href': 'http://haltalk.herokuapp.com/rels/{rel}',
    'name': 'ht',
    'templated': True}],
  'ht:user': [{'href': '/users/mike', 'title': 'Mike Kelly'}],
  'self': {'href': '/users'}},
  'name': "jkj"
}

N1 = HALNavigator.init_from_hal_json('http://haltalk.herokuapp.com', simplejson.dumps(hal_json))
print N1()
print N1.links
print N1['ht:user'][0]