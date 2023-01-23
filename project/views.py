from flask import Blueprint, render_template, request, redirect
from .models import tests

views = Blueprint("views", __name__)

@views.route('/', methods=['GET'])
def index():
    test_names = tests.query.all()
    return render_template('index.html', tests=test_names)

@views.route('/help', methods=['GET'])
def help():
    return render_template('help.html')

@views.route('/login', methods=['GET'])
def login():
    return render_template('login.html')