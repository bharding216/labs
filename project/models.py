from . import db
from sqlalchemy.dialects.mysql import BLOB
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import Flask
from sqlalchemy import DateTime, Text


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
    state = db.Column(db.String(2))
    country = db.Column(db.String(2))
    photo = db.Column(BLOB)
    email = db.Column(db.String(100))
    major_category = db.Column(db.String(100))
    minor_category = db.Column(db.String(100))
    website_url = db.Column(db.String(100))
    point_of_contact = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    lab_description = db.Column(Text(length='medium'))
    tests = db.relationship('tests', secondary='labs_tests', back_populates='labs')
    lab_logins = db.relationship('labs_login', backref='labs', lazy=True)

class labs_tests(db.Model):
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), primary_key=True)
    price = db.Column(db.Numeric(10,2))
    turnaround = db.Column(db.Integer)
    test_description = db.Column(Text(length='medium'))
    certifications = db.Column(Text(length='medium'))

class labs_login(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    lab_name = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(512), nullable=False)
    type = db.Column(db.String(15))
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'))

class individuals_login(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(512), nullable=False)
    company_name = db.Column(db.String(100))
    type = db.Column(db.String(15))


class test_requests(db.Model):
    request_id = db.Column(db.Integer, primary_key=True)
    requestor_id = db.Column(db.Integer, db.ForeignKey('individuals_login.id'), nullable=False)
    number_of_samples = db.Column(db.Integer)
    sample_description = db.Column(db.String(16000000))
    extra_requirements = db.Column(db.String(16000000))
    test_name = db.Column(db.String(100), nullable=False)
    approval_status = db.Column(db.String(100), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    results = db.Column(db.LargeBinary(length=2**32-1))
    payment_status = db.Column(db.String(10))
    transit_status = db.Column(db.String(100))
    datetime_submitted = db.Column(DateTime)
    labs_response = db.Column(db.String(16000000))

class email_subscribers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200))

class test_results(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer)
    lab_id = db.Column(db.Integer)
    date_time_stamp = db.Column(db.String(45))
    filename = db.Column(db.String(150))

class chat_history(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_type = db.Column(db.Integer)
    datetime_submitted = db.Column(DateTime)
    comment = db.Column(Text(length=2**24-1))
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'))
    lab = db.relationship('labs', backref='chat_history')
    customer_id = db.Column(db.Integer, db.ForeignKey('individuals_login.id'))
    customer = db.relationship('individuals_login', backref='chat_history')
