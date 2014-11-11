from restnavigator import HALNavigator

class HALTraversor(object):
    def __init__(self, root_uri):
        self.navigator = HALNavigator(root_uri)
        self.template_parameters = None
        self.request_options_dict = None
        self.request_body = None

    def with_request_options(self, **request_options_dict):
        """
            'default' = **kwargs
            'post' =  **kwargs
            'get' = **kwargs
            'ht:user'= **kwargs
        """

        # Populate as per default
        default_options = request_options_dict.pop('default', {})

        for alias, request_options_dict in default_options.iteritems():
            self.request_options_dict[alias] = request_options_dict
            for header_option in default_options.keys():
                self.request_options_dict[alias].setdefault(header_option, default_options[header_option])
        return self

    def apply_request_options(self, rel_name=None, method=None):
        if self.request_options_dict is not None:
            request_options = self._select_info_for_a_sequence(self.request_options_dict, method, rel_name)
            if 'headers' in request_options:
                self.navigator.session.headers.update(request_options['headers'])
            self.navigator.session.auth = request_options.get('auth')
            self.request_body = request_options.get('body')

            # TODO - Identify other header options to be handled here

    def with_template_parameters(self, **kwargs):
        self.template_parameters = dict(kwargs)
        return self

    def _execute_check(self,method=None,rel_name=None):
        """

            A condition or nested conditions can be defined for a rel name, http_method_name or as default
            If more than one match for a rel name, the look up order is - rel name, method name, default

            Each condition is a tuple consists of two parts -
                First -
                    List of Navigator attributes
                Second -
                    A value or list of values used for equal (==) comparison with values from first part
                    OR
                    A function object which is called with values from first part and expected to return True or False


             'default' = [
                          ('response.status.code',200),
                          ('links', ['ht:user','ht:me']),
                          (('fetched','response.status.code'),(True,200)),
                          ('links', lambda x: 'ht:author' in x),
                          ('state', my_func) #def my_func(navigator): navigator.
                        ]
        """
        if self.conditions_dict is not None:
            conditions = self._select_info_for_a_sequence(self.conditions_dict, method, rel_name)
            for condition in conditions:
                attr,assertion = condition
                if isinstance(attr,basestring):
                    attr = getattr(attr)

                if hasattr(assertion,'__call__'):
                    response = assertion(attr)
                    name = '{}({})'.format(assertion.__name__,attr)
                else:
                    response = attr == assertion
                    name = attr

                if not response:
                    raise 'Validation failed: {} != {} '.format(name)
        return self

    @staticmethod
    def _select_info_for_a_sequence(info_set={}, method=None, rel_name=None):
        return info_set.get(rel_name) \
               or info_set.get(method) \
               or info_set.get('default', {})




    def with_conditions(self, **conditions_dict):
        """
        :conditions_dict -
         'default';[]
         'post':[],
         'get':[],
         'ht:me':[],
        """

        # Populate as per default
        default_conditions = conditions_dict.pop('default', [])
        self.conditions_dict = {alias: (default_conditions + alias_conditions)
                                for alias, alias_conditions in conditions_dict.iteritems()}
        return self

    def follow(self, *sequences):
        """
        :sequences - is a tuple of every sequence to be followed.

            Each sequence can be
            - just rel name
                e.g.
                    'ht:me'
            - a tuple of rel name, http method name and other options to be used to follow rel
                e.g.
                    ('ht:me','post', request_options=options_dict,
                                     template_parameters=param_dict,
                                     condition=condition_dict),

            rel name - is mandatory.

            http method name - optional.
                If no method specified, 'method' property in the link info from its parent HAL response is used
                If link info doesn't have 'method' property, 'GET' is assumed

            options - optional

                This kwargs may have
                "request_options" -  To override options set by 'with_request_options' method.
                "template_parameters" - To override options set by 'with_template_parameters' method.

            Example Sequences:
                    ('ht:me','ht:user')
                    ('ht:me',('ht:user','get'),'ht:posts')
                    (
                        ('ht:me','post', request_options=options_dict,
                                         template_parameters=param_dict,
                                         condition=condition_dict),
                        'ht:user',
                        ('ht:posts','get',request_options=options_dict)
                    )

        :default_options - is a tuple of options
            If there is no option specified as part of sequence info, default_options will be used

            Each option can be
                request_options - See method 'with_request_options' for more details
                conditions - See method 'with_conditions' for more details

        """
        cursor = self.navigator
        for seq in sequences:

            if isinstance(seq, basestring):
                seq = (seq,)

            rel_name = seq[0]
            try:
                method = seq[1]
            except IndexError:
                method = None

            cursor = cursor[rel_name]
            if cursor.templated:
                cursor = cursor.expand(**self.template_parameters)
            self.apply_request_options(method, rel_name)

            if method == 'post':
                cursor = cursor.create({})

        print cursor
        print cursor.links
        return cursor

#
# T = HALTraversor('http://haltalk.herokuapp.com/')
# template_parameters = {'name': 'test321', 'foo': 'boo'}
# condition = {'default': (
#                             ('response.status.code', lambda x: x == 200),
#                             ('response.text', lambda x: 200 in x),
#                             ('links', lambda x: 'ht:author' in x)
#                         ),
#              'post': (),
#              'get': (),
#              'ht:ln': (),
# }
#
# r = T.with_template_parameters(**template_parameters).with_conditions().follow('ht:me',
#                                                                               'ht:posts',
#                                                                               'ht:author')

J= HALTraversor('http://0.0.0.0:7777/')
template_parameters = {'channel': 'online',
                       'date': '2014-11-03',
                       'static_id':'BOX_PACKAGE'}
chset =  J.with_template_parameters(**template_parameters).follow(('create_basket','post'),'products')
print chset.links

from pprint import pprint
pprint(chset())