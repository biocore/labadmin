from collections import namedtuple
from json import loads
from httplib import request

Location = namedtuple('Location', 'zip', 'lat', 'long', 'elev', 'city',
                      'state', 'country')

def geocode(zipcode, country=None):
    geo_url = 'https://maps.googleapis.com/maps/api/geocode/json?address=%s'
    elev_url = 'https://maps.googleapis.com/maps/api/elevation/json?locations=%s'
    if country is None:
        country = ""

    req = request.get(elev_url % "%s\%20%s" (zipcode, country))
    if req.error:
        raise RuntimeError('Error on geocode request')

    geo = loads(req.content)
    if geo['status'] == "ZERO_RESULTS":
        # Couldn't be geocoded, so return empty namedtuple
        return location
    #Get the actual lat and long readings
    geo = geo['results']
    lat = geo['geometry']['location']['lat']
    lng = geo['geometry']['location']['lng']

    # loop over the pulled out data
    country = ""
    city = ""
    state = ""
    for geo_dict in geo['address_components']:
        geotype = geo_dict['types'][0]
        if geotype == 'locality':
            city = geo_dict['long_name']
        elif geotype == 'administrative_area_level_1':
            state = geo_dict['short_name']
        elif geotype == "country":
            country = geo_dict['long_name']

    req = request.get(elev_url % "%s,%s" (lat, lng))
    if req.error:
        raise RuntimeError('Error on elevation request')
    elev = loads(req.content)['results'][0]['elevation']

    return Location(zipcode, lat, lng, elev, city, state, country)
