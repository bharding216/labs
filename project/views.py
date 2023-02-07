from flask import Blueprint, render_template, request, redirect, flash, url_for, session
from flask_login import login_required, current_user
from .models import tests, labs, labs_tests, individuals_login, labs_login
import datetime
from . import db
from flask_mail import Message
from . import db, mail
import bcrypt

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
        return render_template('index.html', tests=test_names, 
                               date=date_choice,
                               user=current_user)

@views.route('/about', methods=['GET'])
def about():
    return render_template('about.html', user = current_user)



@views.route('/labs', methods=['GET', 'POST'])
def lab_function():
    if request.method == 'POST':
        selected_lab_id = request.form['lab_id']
        session['selected_lab_id'] = selected_lab_id
        return redirect(url_for('views.booking'))


    else:
        selected_test = session.get('selected_test')
        row_in_tests_table = tests.query.filter(tests.name == selected_test).first()
        id_in_tests_table = row_in_tests_table.id
        rows_in_labs_tests_table = labs_tests.query.filter(labs_tests.test_id == id_in_tests_table).all()

        #change this to only query labs that can perform that test
        lab_query = labs.query.all()

        return render_template('labs.html', 
            lab_query=lab_query, 
            selected_test=selected_test, 
            price_table = rows_in_labs_tests_table,
            user = current_user
            )


@views.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        requestor_name = request.form['name']
        session['requestor_name'] = requestor_name
        turnaround_time = request.form['turnaround']
        session['turnaround_time'] = turnaround_time
        return redirect(url_for('views.confirmation'))

    else:
        selected_lab_id = session.get('selected_lab_id')
        lab_choice = labs.query.get_or_404(selected_lab_id)
        return render_template('booking.html', lab_choice=lab_choice,
                               user = current_user)



@views.route('/confirmation', methods=['GET'])
def confirmation():
    selected_test = session.get('selected_test')
    requestor_name = session.get('requestor_name')
    turnaround_time = session.get('turnaround_time')

    selected_lab_id = session.get('selected_lab_id')
    lab_choice = labs.query.get_or_404(selected_lab_id)


    return render_template('confirmation.html', 
                           selected_test=selected_test,
                           requestor_name=requestor_name,
                           lab_choice=lab_choice,
                           turnaround_time=turnaround_time,
                           user = current_user
                           )




def send_reset_password_email(user, token):
    reset_password_url = url_for('reset_password', token=token, _external=True)
    message = Message(subject='Reset Your Password',
                      recipients=[user.email],
                      body=f'Reset your password by visiting the following link: {reset_password_url}')
    mail.send(message)


@views.route("/reset_password", methods=["GET", "POST"])
def reset_password_request():
    if request.method == "POST":
        email = request.form.get("email")
        user = individuals_login.query.filter_by(email=email).first()
        if user:
            token = user.generate_reset_token()
            send_reset_password_email(user, token)
        return redirect(url_for("views.index"))

    return render_template("reset_password_request.html")


@views.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = individuals_login.verify_reset_token(token)
    if user is None:
        # the reset token is invalid
        return redirect(url_for("index"))

    if request.method == "POST":
        # get the new password from the form
        new_password = request.form.get("new_password")
        # update the password for the user
        user.set_password(new_password)
        db.session.commit()
        # redirect to some page after password change is successful
        return redirect(url_for("index"))

    return render_template("reset_password.html")
