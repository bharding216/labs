import jwt
import os
from time import time
from . import db
from sqlalchemy.dialects.mysql import BLOB
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import Flask
import yaml


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
    tests = db.relationship('tests', secondary='labs_tests', back_populates='labs')

class labs_tests(db.Model):
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), primary_key=True)
    price = db.Column(db.Numeric(10,2))

class labs_login(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    lab_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(512), nullable=False)
    type = db.Column(db.String(15), nullable=False)

class individuals_login(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(100))
    type = db.Column(db.String(15), nullable=False)


class test_requests(db.Model):
    request_id = db.Column(db.Integer, primary_key=True)
    requestor_id = db.Column(db.Integer, db.ForeignKey('individuals_login.id'), nullable=False)
    sample_name = db.Column(db.String(100))
    sample_description = db.Column(db.String(16000000))
    turnaround = db.Column(db.Integer)
    test_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(100), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)