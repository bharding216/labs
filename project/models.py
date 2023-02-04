from . import db
from sqlalchemy.dialects.mysql import BLOB
from flask_login import UserMixin

class tests(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(16000000))
    labs = db.relationship('labs', secondary='labs_tests', back_populates='tests')

class labs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
    tests = db.relationship('tests', secondary='labs_tests', back_populates='labs')

class labs_tests(db.Model):
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), primary_key=True)
    price = db.Column(db.Numeric(10,2))

class individuals_login(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

class labs_login(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    lab_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)