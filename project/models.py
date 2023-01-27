from . import db
from sqlalchemy.dialects.mysql import BLOB

class tests(db.Model):
    test_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(16000000))

class labs(db.Model):
    lab_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    zip_code = db.Column(db.String(10))
    street_address_1 = db.Column(db.String(100))
    street_address_2 = db.Column(db.String(100))
    city = db.Column(db.String(45))
    state = db.Column(db.String(45))
    country = db.Column(db.String(45))
    photo = db.Column(BLOB)
    email = db.Column(db.String(100))
    major_category = db.Column(db.String(100))
    minor_category = db.Column(db.String(100))
    website_url = db.Column(db.String(100))