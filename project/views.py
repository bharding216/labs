from flask import Blueprint, render_template, request, redirect, flash, url_for, session
from .models import tests, labs, labs_tests
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

    selected_test = request.args.get('selected_test')
    zipcode = request.args.get('zipcode')
    date = request.args.get('date-picker')

    ########
    # Query the labs that can do that test
    ########

    row_in_tests_table = tests.query.filter(tests.name == selected_test).first()
    id_in_tests_table = row_in_tests_table.id
    rows_in_labs_tests_table = labs_tests.query.filter(labs_tests.test_id == id_in_tests_table).all()

    lab_query = labs.query.all()

    return render_template('labs.html', 
        lab_query=lab_query, 
        selected_test=selected_test, 
        price_table = rows_in_labs_tests_table
    )




@views.route('/team', methods=['GET'])
def team():
    return render_template('team.html')


@views.route('/login', methods=['GET'])
def login():
    return render_template('login.html')




@views.route('/booking/<int:id>', methods=['GET'])
def booking(id):
    # Send your lab choice (and all its characteristics)
    # to the booking.html file.
    lab_choice = labs.query.get_or_404(id)

    return render_template('booking.html', lab_choice=lab_choice)


