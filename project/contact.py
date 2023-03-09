from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_required, current_user
from .models import tests, labs, labs_tests
import datetime
import phonenumbers

contact_bp = Blueprint('contact', __name__, 
    template_folder='contact_templates', static_folder='contact_static')



@contact_bp.route('/', methods=['GET', 'POST'])
def contact_function():
    if request.method == 'POST':
        first_name = request.form['first_name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']

        return render_template('contact_success.html', 
                                first_name = first_name,
                                email = email, 
                                phone = phone, 
                                message = message,
                                user = current_user)

    return render_template('contact.html', user = current_user)





@contact_bp.route('/lab_contact', methods=['GET', 'POST'])
def lab_contact():
    if request.method == 'POST':
        first_name = request.form['first_name']
        lab_name = request.form['lab_name']

        return render_template('lab_contact_success.html',
                               user = current_user,
                               first_name = first_name,
                               lab_name = lab_name
                               )

    return render_template('lab_contact.html', 
                           user = current_user)