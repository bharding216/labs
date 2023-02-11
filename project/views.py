from flask import Blueprint, render_template, request, redirect, flash, url_for, session
from flask_login import login_required, current_user, login_user
from .models import tests, labs, labs_tests, individuals_login, labs_login
import datetime
from . import db
from flask_mail import Message
from . import db, mail
from itsdangerous.url_safe import URLSafeSerializer
#from itsdangerous.serializer import Serializer
import yaml
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous.exc import BadSignature


views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_test = request.form['selected_test']
        session['selected_test'] = selected_test

        zipcode = request.form['zipcode']
        date = request.form['date-picker']
        return redirect(url_for('views.lab_function'))

    else:
        test_names = tests.query.all()
        date_choice = datetime.datetime.now().strftime("%Y-%m-%d")
        return render_template('index.html', tests = test_names, 
                               date = date_choice,
                               user = current_user)

@views.route('/about', methods=['GET'])
def about():
    return render_template('about.html', user = current_user)



@views.route('/labs', methods=['GET', 'POST'])
def lab_function():
    if request.method == 'POST':
        selected_lab_id = request.form['lab_id']
        session['selected_lab_id'] = selected_lab_id
        return redirect(url_for('views.user_info'))


    else:
        selected_test = session.get('selected_test')
        row_in_tests_table = tests.query.filter(tests.name == selected_test).first()
        id_in_tests_table = row_in_tests_table.id
        rows_in_labs_tests_table = labs_tests.query.filter(labs_tests.test_id == id_in_tests_table).all()

        #change this to only query labs that can perform that test
        lab_query = labs.query.all()

        return render_template('labs.html', 
            lab_query = lab_query, 
            selected_test = selected_test, 
            price_table = rows_in_labs_tests_table,
            user = current_user
            )


# @views.route('/booking', methods=['GET', 'POST'])
# def booking():
#     if request.method == 'POST':
#         requestor_name = request.form['name']
#         session['requestor_name'] = requestor_name
#         turnaround_time = request.form['turnaround']
#         session['turnaround_time'] = turnaround_time
#         return redirect(url_for('views.confirmation'))

#     else:
#         selected_lab_id = session.get('selected_lab_id')
#         lab_choice = labs.query.get_or_404(selected_lab_id)
#         return render_template('booking.html', 
#                                lab_choice = lab_choice,
#                                user = current_user)



@views.route('/user_info', methods=['GET', 'POST'])
def user_info():
    return render_template('user_info.html', 
                           user = current_user)




@views.route('/new_user_booking', methods=['GET', 'POST'])
def new_user_booking():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        company_name = request.form['company_name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        turnaround = request.form['turnaround']
        sample_description = request.form['sample_description']
        sample_name = request.form['sample_name']

        session['first_name'] = first_name
        session['turnaround'] = turnaround


        email_exists = individuals_login.query.filter_by(email = email).first()
        print(email_exists)
        if email_exists:
            flash('That email is already in use. Please try another email or log in.', category = 'error')
            selected_lab_id = session.get('selected_lab_id')
            lab_choice = labs.query.get_or_404(selected_lab_id)
            return render_template('new_user_booking.html', 
                                   user = current_user,
                                   lab_choice = lab_choice,
                                   first_name = first_name,
                                   last_name = last_name,
                                   company_name = company_name,
                                   email = email,
                                   phone = phone,
                                   password = password,
                                   turnaround = turnaround,
                                   sample_name = sample_name,
                                   sample_description = sample_description)
        else:
            hashed_password = generate_password_hash(password)
            new_user = individuals_login(
                first_name = first_name, 
                last_name = last_name, 
                password = hashed_password, 
                phone = phone, 
                email = email,
                company_name = company_name
                )
            db.session.add(new_user)
            db.session.commit()
            flash('New account successfully created.', category = 'success')
            return redirect(url_for('views.confirmation'))

    else:
        selected_lab_id = session.get('selected_lab_id')
        lab_choice = labs.query.get_or_404(selected_lab_id)

        return render_template('new_user_booking.html', 
                               user = current_user,
                               lab_choice = lab_choice)



@views.route("/returning_user_login", methods=['GET', 'POST'])
def returning_user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        individual_email = individuals_login.query.filter_by(email = email).first()
        if individual_email:
            if check_password_hash(individual_email.password, password):
                login_user(individual_email, remember=False)
                session.permanent = True
                flash('Login successful!', category = 'success')
                return redirect(url_for('views.returning_user_booking'))
            
            else:
                flash('Incorrect password. Please try again.', category = 'error')
                return render_template('returning_user_login.html', 
                                       user = current_user, 
                                       email = email)
        else:
            flash('That email is not associated with an account. Please check for typos.', category = 'error')
            return render_template('returning_user_login.html', 
                                   user = current_user, 
                                   email = email)

    return render_template('returning_user_login.html', user = current_user)



@views.route("/returning_user_booking", methods=['GET', 'POST'])
def returning_user_booking():
    selected_lab_id = session.get('selected_lab_id')
    lab_choice = labs.query.get_or_404(selected_lab_id)
    return render_template('returning_user_booking.html', 
                            user = current_user,
                            lab_choice = lab_choice)



@views.route('/confirmation', methods=['GET', 'POST'])
def confirmation():
    selected_test = session.get('selected_test')
    first_name = session.get('first_name', None)
    turnaround = session.get('turnaround')

    selected_lab_id = session.get('selected_lab_id')
    lab_choice = labs.query.get_or_404(selected_lab_id)


    return render_template('confirmation.html', 
                           selected_test = selected_test,
                           first_name = first_name,
                           lab_choice = lab_choice,
                           turnaround = turnaround,
                           user = current_user
                           )










@views.route("/reset_password", methods=["GET", "POST"])
def reset_password_request():
    if request.method == "POST":
        email = request.form.get("email")
        session['email'] = email
        user = individuals_login.query.filter_by(email=email).first()
        if user:
            current_time = datetime.datetime.now().time()
            current_time_str = current_time.strftime('%H:%M:%S')
            with open('project/db.yaml', 'r') as file:
                test = yaml.load(file, Loader=yaml.FullLoader)

            s = URLSafeSerializer(test['secret_key'])
            # dumps => take in a list and create a serialize it into a string representation.
            # returns a string representation of the data - encoded using the secret key.
            token = s.dumps([email, current_time_str])

            reset_password_url = url_for('views.reset_password', token = token, _external=True)

            msg = Message('New Password Request', 
                sender = 'hello@carbonfree.dev', 
                recipients = ['bharding@carbonfree.cc'],
                body=f'Reset your password by visiting the following link: {reset_password_url}')

            mail.send(msg) 
            flash('Email successfully sent.', category = 'success')

        else:
            flash('That email does not exist in our system.', category = 'error')
            return redirect(url_for('views.reset_password_request'))
        return redirect(url_for('views.reset_password_request'))
    
    else:
        return render_template("reset_password_form.html", 
                               user = current_user)





@views.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":

        with open('project/db.yaml', 'r') as file:
            test = yaml.load(file, Loader=yaml.FullLoader)

        s = URLSafeSerializer(test['secret_key'])
        
        original_email = session.get('email')

        try: 
            # loads => take in a serialized string and generate the original string inputs.
            token_email = (s.loads(token))[0]

        except BadSignature:
            flash('You do not have permission to change the password for this email.', category = 'error')
            return redirect(url_for('views.reset_password', token = token))

        if token_email == original_email:
            new_password = request.form.get("new_password")
            hashed_password = generate_password_hash(new_password)
            user = individuals_login.query.filter_by(email = token_email).first()
            user.password = hashed_password

            #db.session.commit()
            flash('Your password has been successfully updated!', category = 'success')
            return redirect(url_for('views.reset_password', token = token))

    else:
        return render_template("reset_password.html", 
                               user = current_user, 
                               token = token
                               )
