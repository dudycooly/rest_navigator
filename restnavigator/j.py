__author__ = 'jp'
import json
from halnav import HALNavigator

hal_response = json.dumps({"_links": {
    "self": {
        "href": "http://localhost:8082/stubs/webapi/standard_sales_journey/317ac200-5bbe-11e4-8483-ac162d83e178"
    },
    "orca:customer-portfolio": {
        "templated": False,
        "method": "GET",
        "href": "http://localhost:8082/stubs/webapi/standard_sales_journey/317ac200-5bbe-11e4-8483-ac162d83e178/customer_portfolio"
    },
    "orca:set-directory-listing-preference": {
        "method": "PUT",
        "href": "http://localhost:8082/stubs/webapi/standard_sales_journey/317ac200-5bbe-11e4-8483-ac162d83e178/directory_listing_preference"
    },
    "orca:submit-order": {
        "templated": False,
        "method": "POST",
        "href": "http://localhost:8082/stubs/webapi/submit_order/317ac200-5bbe-11e4-8483-ac162d83e178"
    },
    "orca:dn-check": {
        "templated": True,
        "method": "GET",
        "href": "http://localhost:8082/stubs/webapi/standard_sales_journey/317ac200-5bbe-11e4-8483-ac162d83e178/dn-check?directory_number={directory_number}"
    },
    "orca:create-basket": {
        "templated": False,
        "method": "POST",
        "href": "http://localhost:8082/stubs/webapi/standard_sales_journey/317ac200-5bbe-11e4-8483-ac162d83e178/basket"
    },
    "orca:get-interaction-resources": {
        "method": "GET",
        "href": "http://localhost:8082/stubs/webapi/interaction/get_interaction_resources/c99aac1dc4f34f6294941d1f3138e2c9"
    },
    "orca:find-addresses": {
        "templated": True,
        "method": "GET",
        "href": "http://localhost:8082/stubs/webapi/standard_sales_journey/317ac200-5bbe-11e4-8483-ac162d83e178/find_addresses?postcode={postcode}"
    }
}})

N = HALNavigator.init_with_hal_json('http://localhost:8082', hal_response)

print N.links
