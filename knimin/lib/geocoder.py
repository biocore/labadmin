from collections import namedtuple
from json import loads
import requests

Location = namedtuple('Location', ['zip', 'lat', 'long', 'elev', 'city',
                      'state', 'country'])


def geocode(zipcode, country=None):
    geo_url = 'https://maps.googleapis.com/maps/api/geocode/json?address=%s'
    elev_url = 'https://maps.googleapis.com/maps/api/elevation/json?locations=%s'
    if country is None:
        country = ""

    req = requests.get(geo_url % "%s %s" % (zipcode, country))
    if req.status_code != 200:
        raise IOError('Error on geocode request')

    geo = loads(req.content)
    if geo['status'] == "ZERO_RESULTS":
        # Couldn't be geocoded, so return empty namedtuple
        return Location(zipcode, None, None,  None,  None, None, None)
    # Get the actual lat and long readings
    geo = geo['results'][0]
    lat = geo['geometry']['location']['lat']
    lng = geo['geometry']['location']['lng']

    # loop over the pulled out data
    ctry = ""
    city = ""
    state = ""
    for geo_dict in geo['address_components']:
        geotype = geo_dict['types'][0]
        if geotype == 'locality':
            city = geo_dict['long_name']
        elif geotype == 'administrative_area_level_1':
            state = geo_dict['short_name']
        elif geotype == "country":
            ctry = geo_dict['long_name']

    req2 = requests.get(elev_url % "%s,%s" % (lat, lng))
    if req2.status_code != 200:
        raise IOError('Error on elevation request')
    elev = loads(req2.content)['results'][0]['elevation']

    return Location(zipcode, lat, lng, elev, city, state, ctry)
