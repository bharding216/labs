from flask import Blueprint, render_template, request, redirect
from .models import tests, labs
import datetime

views = Blueprint('views', __name__)

@views.route('/', methods=['GET'])
def index():
    test_names = tests.query.all()
    date_choice = datetime.datetime.now().strftime("%Y-%m-%d")
    return render_template('index.html', tests=test_names, date=date_choice)

@views.route('/about', methods=['GET'])
def about():
    return render_template('about.html')

@views.route('/labs', methods=['GET'])
def lab_function():
    lab_query = labs.query.all()
    return render_template('labs.html', lab_query=lab_query)

@views.route('/team', methods=['GET'])
def team():
    return render_template('team.html')


@views.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@views.route('/booking', methods=['GET'])
def booking():
    return render_template('booking.html')