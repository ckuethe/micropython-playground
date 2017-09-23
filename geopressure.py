# vim: tabstop=4:softtabstop=4:shiftwidth=4:expandtab:

from math import sin, cos, asin, sqrt, radians
try:
    from urequests import get
except ImportError:
    from requests import get


def mk_queryparams(params):
    query = []
    for k,v in params.items():
        query.append('{}={}'.format(k,v))
    return '?'+'&'.join(query)

class GeoPressure(object):
    #This class does uses some web services to estimate your local sea level
    #pressure. It does this by first estimating location with a GeoIP service,
    #then querying aviationweather.gov to find the nearest airport with METAR
    #data, then fetching its most recent METAR report. If the report includes
    #a sea level pressure measurement it is reported; if not it is calculated
    #from the reported pressure and altitude.
    #Just as aircraft need to adjust their altimeters to local pressure, users
    #of pressure sensors (eg. BME280 or BMP085) use this to calculate altitude.
    def __init__(self):
        self._url = 'http://aviationweather.gov/adds/dataserver_current/httpparam'
        self.location = {'lat':None, 'lon':None}
        self.airport = None
        self.metar = None

    def haversine(self, p1, p2):
        # Great circle distance, used to find nearest airport. p1 and p2
        # are 2-element dicts containing 'lat' and 'lon'
        # Based on https://rosettacode.org/wiki/Haversine_formula#Python
        p1 = {'lat': float(p1['lat']), 'lon': float(p1['lon'])}
        p2 = {'lat': float(p2['lat']), 'lon': float(p2['lon'])}

        earth_radius = 3959.87433  #  miles
        # earth_radius = 6372.8  #  kilometers
        d_lat = radians(p2['lat'] - p1['lat'])
        d_lon = radians(p2['lon'] - p1['lon'])

        arclen = sin(d_lat / 2)**2 + cos(p1['lat']) * cos(p2['lat']) * sin(d_lon / 2)**2
        chord = 2 * asin(sqrt(arclen))

        return earth_radius * chord

    def alt_baro_to_slp(self, altitude=0, in_hg=None, millibar=None):
        # Given a known altitude and observed pressure
        # reading, calculate sea level pressure
        if in_hg is not None and millibar is not None:
            raise ValueError("Only one of in_hg or millibar may be specified")
        if in_hg is not None:
            millibar = float(in_hg) * 33.8639

        return millibar / (1 - float(altitude) / 44330.0)**5.255

    def get_geoip(self, target_ip=''):
        # Guess system location from IP.
        # http://ip-api.com/docs/api:json
        #
        #  {u'as': u'AS2828 XO Communications',
        #    u'city': u'San Francisco',
        #    u'country': u'United States',
        #    u'countryCode': u'US',
        #    u'isp': u'XO Communications',
        #    u'lat': 37.7484,
        #    u'lon': -122.4156,
        #    u'org': u'XO Communications',
        #    u'query': u'209.31.243.194',
        #    u'region': u'CA',
        #    u'regionName': u'California',
        #    u'status': u'success',
        #    u'timezone': u'America/Los_Angeles',
        #    u'zip': u'94110'}
        result = get('http://ip-api.com/json/{}'.format(target_ip)).json()
        
        self.location = {'lat': float(result['lat']), 'lon': float(result['lon'])}
        return self.location

    def get_stations(self, near, distance=10):
        # Find nearby acceptable airport weather stations
        # https://www.aviationweather.gov/dataserver
        #   {'country': 'US',
        #   'distance': 0.0,
        #   'elevation_m': '3.0',
        #   'latitude': '37.62',
        #   'longitude': '-122.37',
        #   'site': 'SAN FRANCISCO',
        #   'site_type': ['METAR', 'TAF'],
        #   'state': 'CA',
        #   'station_id': 'KSFO',
        #   'wmo_id': '72494'}

        params = {'dataSource': 'stations',
                  'requestType': 'retrieve',
                  'format': 'csv',
                  'radialDistance': '{};{},{}'.format(distance, near['lon'], near['lat'])}
        resp = get(self._url+mk_queryparams(params))
        if resp.status_code != 200:
            return None

        rows = str(resp.text).strip().split('\n')[5:]
        fields = rows[0].split(',')
        ret_val = []
        for row in rows[1:]:
            data = map(lambda x: x.strip(), row.split(','))
            station = dict(zip(fields, data))
            station['distance'] = self.haversine(near, {'lat': station['latitude'], 'lon':station['longitude']})

            station['site_type'] = station.get('site_type', '').split()
            if 'METAR' in station['site_type']:  # only use this airport if it has METARS.
                ret_val.append(station)
        ret_val.sort(key=lambda x: x['distance'])
        return ret_val

    def get_metar(self, icao='KSFO', hours=2):
        # Get the METAR for a specific airport
        # https://www.aviationweather.gov/dataserver
        #   {'altim_in_hg': '29.870079',
        #   'auto': '',
        #   'auto_station': 'TRUE',
        #   'cloud_base_ft_agl': '',
        #   'corrected': '',
        #   'dewpoint_c': '12.8',
        #   'elevation_m': '3.0',
        #   'flight_category': 'VFR',
        #   'freezing_rain_sensor_off': '',
        #   'latitude': '37.62',
        #   'lightning_sensor_off': '',
        #   'longitude': '-122.37',
        #   'maintenance_indicator_on': '',
        #   'maxT24hr_c': '',
        #   'maxT_c': '',
        #   'metar_type': 'METAR',
        #   'minT24hr_c': '',
        #   'minT_c': '',
        #   'no_signal': '',
        #   'observation_time': '2017-09-21T01:56:00Z',
        #   'pcp24hr_in': '',
        #   'pcp3hr_in': '',
        #   'pcp6hr_in': '',
        #   'precip_in': '',
        #   'present_weather_sensor_off': '',
        #   'raw_text': 'KSFO 210156Z 26014G18KT 10SM FEW007 SCT013 \
        #                BKN100 18/13 A2987 RMK AO2 SLP115 T01780128',
        #   'sea_level_pressure_mb': '1011.5',
        #   'sky_cover': '',
        #   'snow_in': '',
        #   'station_id': 'KSFO',
        #   'temp_c': '17.8',
        #   'three_hr_pressure_tendency_mb': '',
        #   'vert_vis_ft': '',
        #   'visibility_statute_mi': '10.0',
        #   'wind_dir_degrees': '260',
        #   'wind_gust_kt': '18',
        #   'wind_speed_kt': '14',
        #   'wx_string': ''}
        params = {'dataSource': 'metars',
                  'requestType': 'retrieve',
                  'format': 'csv',
                  'stationString': icao,
                  'hoursBeforeNow': hours}
        resp = get(self._url+mk_queryparams(params))
        if resp.status_code != 200:
            return None

        rows = str(resp.text).strip().split('\n')
        ret_val = []
        fields = rows[5].split(',')
        for row in rows[6:]:
            data = row.split(',')
            metar = dict(zip(fields, data))
            ret_val.append(metar)
        return ret_val

    def __call__(self, target_ip='', near=None, airport=None, distance=10):
        # shim around get_slp()
        return self.get_slp(target_ip, near, airport, distance)

    def get_slp(self, target_ip='', near=None, airport=None, distance=10):
        # All-in-one sea level pressure calculation
        if airport is None:
            if near is not None and isinstance(near, dict):
                self.location = near
            else:
                geo = self.get_geoip(target_ip)

            # XXX figure out how to auto-scan for the nearest
            # XXX airport if there isn't one in a fixed distance
            stations = self.get_stations(self.location, distance)
        else:
            stations = [airport]

        metar = None
        for airport in stations:
            metar = self.get_metar(airport['station_id'])[0]
            if 'raw_text' in metar:  # your nearest airport may not have an operational station
                break

        if metar['sea_level_pressure_mb'] == '':
            metar["computed sea level pressure"] = True
            metar['sea_level_pressure_mb'] = self.alt_baro_to_slp(metar['elevation_m'],
                                                                  in_hg=metar['altim_in_hg'])
        self._metar = metar
        self._airport = metar['station_id']

        return float(metar['sea_level_pressure_mb'])

if __name__ == '__main__':
    geopressure = GeoPressure()
    print(geopressure())
