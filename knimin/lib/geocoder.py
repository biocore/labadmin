from collections import namedtuple
from json import loads
import requests
from time import sleep


class GoogleAPILimitExceeded(Exception):
    pass


class GoogleAPIRequestDenied(Exception):
    pass


class GoogleAPIInvalidRequest(Exception):
    pass

Location = namedtuple('Location', ['input', 'lat', 'long', 'elev', 'city',
                      'state', 'postcode', 'country'])


def _call_wrapper(url):
    """Encapsulate all checks for API calls"""
    # allow 4 retries do we sleep longer than a second if all loops happen
    for retry in range(4):
        req = requests.get(url)
        if req.status_code != 200:
            raise IOError('Error %d on request: %s\n%s' %
                          (req.status_code, url, req.content))

        geo = loads(req.content)
        if geo['status'] == "OK":
            break
        elif geo['status'] == "OVER_QUERY_LIMIT":
            # sleep in case we're over the 5 requests/sec limit
            sleep(0.3)
        elif geo['status'] == "ZERO_RESULTS":
            return {}
        elif geo['status'] == "REQUEST_DENIED":
            raise GoogleAPIRequestDenied()
        elif geo['status'] == "INVALID_REQUEST":
            raise GoogleAPIInvalidRequest(url)

    if geo['status'] == "OVER_QUERY_LIMIT":
        raise GoogleAPILimitExceeded("Exceeded max calls per day")
    if geo['status'] == "UNKNOWN_ERROR":
        raise IOError("Unknown server error in Google API: %s" % req.content)
    return geo['results']


def geocode(address):
    geo_url = 'https://maps.googleapis.com/maps/api/geocode/json?address=%s'
    elev_url = 'https://maps.googleapis.com/maps/api/elevation/json?locations=%s'

    geo = _call_wrapper(geo_url % address)
    if not geo:
        return Location(address, None, None, None, None, None, None, None)
    # Get the actual lat and long readings
    geo = geo[0]
    lat = float(geo['geometry']['location']['lat'])
    lng = float(geo['geometry']['location']['lng'])

    # loop over the pulled out data
    country = None
    city = None
    state = None
    postcode = None
    for geo_dict in geo['address_components']:
        if not geo_dict['types']:
            continue
        geotype = geo_dict['types'][0]
        if geotype == 'locality' or geotype == "postal_town":
            city = geo_dict['long_name']
        elif geotype == 'administrative_area_level_1':
            state = geo_dict['short_name']
        elif geotype == "country":
            country = geo_dict['long_name']
        elif geotype == "postal_code" or geotype == "postal_code_prefix":
            postcode = geo_dict['long_name']
    geo2 = _call_wrapper(elev_url % "%s,%s" % (lat, lng))
    elev = float(geo2[0]['elevation'])

    return Location(address, lat, lng, elev, city, state, postcode, country)
