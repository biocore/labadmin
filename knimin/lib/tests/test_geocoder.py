from unittest import TestCase, main
from json import loads
import httpretty
from knimin.lib.geocoder import (
    GoogleAPIInvalidRequest, GoogleAPILimitExceeded, GoogleAPIRequestDenied,
    Location, _call_wrapper, geocode)


class TestCallWrapper(TestCase):
    def setUp(self):
        httpretty.enable()
        self.url = 'mock://maps.googleapis.com/%s'

    def tearDown(self):
        httpretty.disable()
        httpretty.reset()

    def test_call_wrapper_ok(self):
        full_url = self.url % 'ok'
        httpretty.register_uri(httpretty.GET, full_url, body=ok,
                               content_type='text/json')

        obs = _call_wrapper(full_url)
        exp = loads(ok)['results']
        self.assertEqual(obs, exp)

    def test_call_wrapper_exceeded_limit(self):
        full_url = self.url % 'exceeded'
        httpretty.register_uri(httpretty.GET, full_url, body=over_query_limit,
                               content_type='text/json')

        with self.assertRaises(GoogleAPILimitExceeded):
            _call_wrapper(full_url)

    def test_call_wrapper_zero_results(self):
        full_url = self.url % 'zero'
        httpretty.register_uri(httpretty.GET, full_url, body=zero_results,
                               content_type='text/json')

        obs = _call_wrapper(full_url)
        self.assertEqual(obs, {})

    def test_call_wrapper_request_denied(self):
        full_url = self.url % 'denied'
        httpretty.register_uri(httpretty.GET, full_url, body=request_denied,
                               content_type='text/json')

        with self.assertRaises(GoogleAPIRequestDenied):
            _call_wrapper(full_url)

    def test_call_wrapper_invalid_request(self):
        full_url = self.url % 'invalid'
        httpretty.register_uri(httpretty.GET, full_url, body=invalid_request,
                               content_type='text/json')

        with self.assertRaises(GoogleAPIInvalidRequest):
            _call_wrapper(full_url)

    def test_call_wrapper_unknown_error(self):
        full_url = self.url % 'unknown'
        httpretty.register_uri(httpretty.GET, full_url, body=unknown_error,
                               content_type='text/json')

        with self.assertRaises(IOError):
            _call_wrapper(full_url)

    def test_call_wrapper_404(self):
        full_url = self.url % '404'
        httpretty.register_uri(httpretty.GET, full_url, body='', status=404)

        with self.assertRaises(IOError):
            _call_wrapper(full_url)

# Results copied from Google API responses on 2015-10-25
ok = '''{
   "results" : [
      {
         "address_components" : [
            {
               "long_name" : "9500",
               "short_name" : "9500",
               "types" : [ "street_number" ]
            },
            {
               "long_name" : "Gilman Drive",
               "short_name" : "Gilman Dr",
               "types" : [ "route" ]
            },
            {
               "long_name" : "Torrey Pines",
               "short_name" : "Torrey Pines",
               "types" : [ "neighborhood", "political" ]
            },
            {
               "long_name" : "La Jolla",
               "short_name" : "La Jolla",
               "types" : [ "sublocality_level_1", "sublocality", "political" ]
            },
            {
               "long_name" : "San Diego",
               "short_name" : "San Diego",
               "types" : [ "locality", "political" ]
            },
            {
               "long_name" : "San Diego County",
               "short_name" : "San Diego County",
               "types" : [ "administrative_area_level_2", "political" ]
            },
            {
               "long_name" : "California",
               "short_name" : "CA",
               "types" : [ "administrative_area_level_1", "political" ]
            },
            {
               "long_name" : "United States",
               "short_name" : "US",
               "types" : [ "country", "political" ]
            },
            {
               "long_name" : "92093",
               "short_name" : "92093",
               "types" : [ "postal_code" ]
            }
         ],
         "formatted_address" : "9500 Gilman Dr, La Jolla, CA 92093, USA",
         "geometry" : {
            "location" : {
               "lat" : 32.8794081,
               "lng" : -117.2368167
            },
            "location_type" : "ROOFTOP",
            "viewport" : {
               "northeast" : {
                  "lat" : 32.8807570802915,
                  "lng" : -117.2354677197085
               },
               "southwest" : {
                  "lat" : 32.8780591197085,
                  "lng" : -117.2381656802915
               }
            }
         },
         "place_id" : "ChIJRVZ32eoG3IART7MHgoYnGCA",
         "types" : [ "street_address" ]
      },
      {
         "address_components" : [
            {
               "long_name" : "9500",
               "short_name" : "9500",
               "types" : [ "street_number" ]
            },
            {
               "long_name" : "Gilman Drive",
               "short_name" : "Gilman Dr",
               "types" : [ "route" ]
            },
            {
               "long_name" : "Torrey Pines",
               "short_name" : "Torrey Pines",
               "types" : [ "neighborhood", "political" ]
            },
            {
               "long_name" : "La Jolla",
               "short_name" : "La Jolla",
               "types" : [ "sublocality_level_1", "sublocality", "political" ]
            },
            {
               "long_name" : "San Diego",
               "short_name" : "San Diego",
               "types" : [ "locality", "political" ]
            },
            {
               "long_name" : "San Diego County",
               "short_name" : "San Diego County",
               "types" : [ "administrative_area_level_2", "political" ]
            },
            {
               "long_name" : "California",
               "short_name" : "CA",
               "types" : [ "administrative_area_level_1", "political" ]
            },
            {
               "long_name" : "United States",
               "short_name" : "US",
               "types" : [ "country", "political" ]
            },
            {
               "long_name" : "92037",
               "short_name" : "92037",
               "types" : [ "postal_code" ]
            }
         ],
         "formatted_address" : "9500 Gilman Dr, San Diego, CA 92037, USA",
         "geometry" : {
            "bounds" : {
               "northeast" : {
                  "lat" : 32.8892575,
                  "lng" : -117.2409763
               },
               "southwest" : {
                  "lat" : 32.8870301,
                  "lng" : -117.2436397
               }
            },
            "location" : {
               "lat" : 32.8879121,
               "lng" : -117.2422584
            },
            "location_type" : "APPROXIMATE",
            "viewport" : {
               "northeast" : {
                  "lat" : 32.8894927802915,
                  "lng" : -117.2409590197085
               },
               "southwest" : {
                  "lat" : 32.8867948197085,
                  "lng" : -117.2436569802915
               }
            }
         },
         "place_id" : "ChIJk4TdaOsG3IAR85v_Fns53PI",
         "types" : []
      }
   ],
   "status" : "OK"
}'''

unknown_error = '''{
   "results" : [],
   "status" : "UNKNOWN_ERROR"
}'''

over_query_limit = '''{
   "results" : [],
   "status" : "OVER_QUERY_LIMIT"
}'''

zero_results = '''{
   "results" : [],
   "status" : "ZERO_RESULTS"
}'''

request_denied = '''{
   "results" : [],
   "status" : "REQUEST_DENIED"
}'''

invalid_request = '''{
   "results" : [],
   "status" : "INVALID_REQUEST"
}'''

if __name__ == '__main__':
    main()
