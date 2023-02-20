from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .models import individuals_login, labs_login
import datetime
from . import db
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__, template_folder='auth_templates', static_folder='auth_static')


@auth_bp.route("/lab", methods=['GET', 'POST'])
def provider_login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        lab = labs_login.query.filter_by(email = email).first()
        if lab:
            if check_password_hash(lab.password, password):
                login_user(lab, remember = False)
                session.permanent = True
                session['type'] = 'lab'
                flash('Login successful!', category='success')
                return redirect(url_for('views.index'))
            else:
                flash('Incorrect password. Please try again.', category = 'error')
        else:
            flash('That email is not associated with an account.', category = 'error')

    return render_template('lab_login.html', user = current_user)



@auth_bp.route("/individual", methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        user = individuals_login.query.filter_by(email = email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember = True)
                session.permanent = True
                session['type'] = 'requestor'
                flash('Login successful!', category = 'success')
                return redirect(url_for('views.index'))
            else:
                flash('Incorrect password. Please try again.', category = 'error')
        else:
            flash('That email is not associated with an account.', category = 'error')

    return render_template('user_login.html', user = current_user)


# New lab signup
@auth_bp.route("/lab_signup", methods=['GET', 'POST'])
def lab_signup():
    if request.method == "POST":
        lab_name = request.form['name']
        lab_email = request.form['email']
        lab_phone = request.form['phone']
        password1 = request.form['password1']
        password2 = request.form['password2']

        if password1 != password2:
            flash('Passwords do not match.', category='error')

        else:
            hashed_password = generate_password_hash(password1)
            new_lab = labs_login(lab_name = lab_name,
                                 password = hashed_password,
                                 phone = lab_phone, 
                                 email = lab_email,
                                 type = 'lab'
                                 )
            db.session.add(new_lab)
            db.session.commit()
            flash('Lab successfully added to database.', category='success')
            return redirect(url_for('views.index'))

    return render_template('lab_signup.html', user=current_user)


# New user signup
@auth_bp.route("/user_signup", methods=['GET', 'POST'])
def user_signup():
    if request.method == "POST":
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        company = request.form['company_name']
        password1 = request.form['password1']
        password2 = request.form['password2']

        if password1 != password2:
            flash('Passwords do not match.', category='error')

        else:
            hashed_password = generate_password_hash(password1)
            new_user = individuals_login(first_name=first_name,
                                         last_name=last_name, 
                                         password=hashed_password, 
                                         phone=phone, 
                                         email=email,
                                         company_name = company,
                                         type = 'requestor'
                                         )
            db.session.add(new_user)
            db.session.commit()
            flash('User successfully added to database.', category='success')
            return redirect(url_for('views.index'))

    return render_template('user_signup.html', user=current_user)








@auth_bp.route("/logout")
@login_required
def logout():
    flash('User successfully logged out', category='success')
    logout_user()

    return redirect(url_for('views.index'))