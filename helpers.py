from flask import url_for, current_app, request
import requests, math, pgeocode

# helpers.py

def my_enumerate(seq, start=0):
    return enumerate(seq, start)

def generate_sitemap():
    with current_app.app_context():
        base_url = request.host_url
        sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for rule in current_app.url_map.iter_rules():
            if "GET" in rule.methods and not bool(rule.arguments):
                endpoint = url_for(rule.endpoint)
                url = base_url.rstrip('/') + endpoint
                sitemap_xml += f'\t<url><loc>{url}</loc></url>\n'
        sitemap_xml += '</urlset>\n'
        return sitemap_xml
    

def get_lat_long_from_zipcode(zipcode):
    nomi = pgeocode.Nominatim('us')
    location = nomi.query_postal_code(zipcode)
    latitude = location.latitude
    longitude = location.longitude
    return latitude, longitude


def distance_calculation(user_latitude, user_longitude, lab_latitude, lab_longitude):
    user_lat_rad = math.radians(user_latitude)
    user_lng_rad = math.radians(user_longitude)
    lab_lat_rad = math.radians(lab_latitude)
    lab_lng_rad = math.radians(lab_longitude)

    earth_radius = 3963.19 # miles

    term1 = (math.sin((user_lat_rad-lab_lat_rad)/2)) ** 2
    term2 = (math.cos(user_lat_rad))*(math.cos(lab_lat_rad))*((math.sin((user_lng_rad-lab_lng_rad)/2)) ** 2)
    whole_term = math.asin((term1 + term2) ** 0.5)
    distance = 2 * whole_term * earth_radius # miles

    return distance
