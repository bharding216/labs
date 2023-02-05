from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .models import individuals_login, labs_login
import datetime
from . import db
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__, template_folder='auth_templates', static_folder='auth_static')


@auth_bp.route("/lab", methods=['GET', 'POST'])
def lab_login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        lab = labs_login.query.filter_by(email=email).first()
        if lab:
            if check_password_hash(lab.password, password):
                login_user(lab, remember=False)
                session.permanent = True
                return redirect(url_for('views.index'))
            else:
                return redirect(url_for('views.about'))

    return render_template('lab_login.html', user=current_user)



@auth_bp.route("/individual", methods=['GET', 'POST'])
def individual_login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        individual_email = labs_login.query.filter_by(email=email).first()
        if individual_email:
            if check_password_hash(labs_login.password, password):
                flash('Successfully logged in!', category='success')
                login_user(individual_email, remember=False)
                session.permanent = True
                return redirect(url_for('views.index'))
            else:
                flash('Password is incorrect. Please try again.', 
                    category='error')
        else:
            flash('That username does not exist. Please try again or contact \
                your system administrator.', 
                category='error')

    flash('Please log in to continue.', category='error')       

    return render_template('user_login.html', user=current_user)


@auth_bp.route("/signup", methods=['GET', 'POST'])
def lab_signup():
    if request.method == "POST":
        username = request.form['username']
        #lab_name = request.form['lab_name']
        #lab_email = request.form['email']
        #phone = request.form['phone']
        password1 = request.form['password1']
        password2 = request.form['password2']

        #email_exists = lab_login.query.filter_by(lab_email=lab_email).first()
        #if email_exists:
        #    flash('Email is already in use. \
        #    Choose another email.', category='error')


        if password1 != password2:
            flash('Passwords do not match.', category='error')
            return redirect(url_for('views.about'))

        else:
            hashed_password = generate_password_hash(password1)
            new_user = labs_login(lab_name=username, password=hashed_password, phone=username, email=username)
            db.session.add(new_user)
            db.session.commit()
            flash("Thanks for signing up!", category='success')
            return redirect(url_for('views.index'))


    return render_template('lab_signup.html', user=current_user)






@auth_bp.route("/lab_logout")
@login_required
def lab_logout():
    logout_user()

    return redirect(url_for('auth.lab_login'))