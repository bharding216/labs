from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_required, current_user
from .models import tests, labs, labs_tests
from flask_mail import Mail, Message
from project import mail
import datetime
import phonenumbers
import os
import requests

contact_bp = Blueprint('contact', __name__, 
    template_folder='contact_templates', static_folder='static')


@contact_bp.route('/', methods=['GET', 'POST'])
def contact_function():
    if request.method == 'POST':
        # Get the reCAPTCHA response from the form
        recaptcha_response = request.form.get('g-recaptcha-response')
        if recaptcha_response:
            # Verify the reCAPTCHA response using the Google reCAPTCHA API
            response = requests.post('https://www.google.com/recaptcha/api/siteverify',
                                    data={'secret': os.getenv('recaptcha_secret_key'), 
                                        'response': recaptcha_response,
                                        'action': 'contact'})

            if response.json()['success']:
                # Process the form data
                first_name = request.form['first_name']
                last_name = request.form['last_name']
                user_email = request.form['email']
                phone = request.form['phone']
                user_message = request.form['message']

                msg = Message('New Contact Form Submission',
                                sender = ("USL Contact Form", 'hello@unifiedsl.com'),
                                recipients = ['team@unifiedsl.com'
                                            ]
                                )
                
                msg.html = render_template('contact_email.html',
                                        first_name = first_name,
                                        last_name = last_name,
                                        user_email = user_email,
                                        phone = phone,
                                        user_message = user_message,
                                        customer_type = 'Customer')

                mail.send(msg)

                return render_template('contact_success.html', 
                                        first_name = first_name,
                                        email = user_email, 
                                        phone = phone, 
                                        message = user_message,
                                        user = current_user)

            else:
                flash('Invalid reCAPTCHA. Please try again.')
        else:
            flash('Please complete the reCAPTCHA.')


    recaptcha_site_key = os.getenv('recaptcha_site_key')
    return render_template('contact.html', 
                           user = current_user,
                           recaptcha_site_key = recaptcha_site_key)





@contact_bp.route('/lab_contact', methods=['GET', 'POST'])
def lab_contact():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        lab_name = request.form['lab_name']
        title = request.form['title']
        user_email = request.form['email']
        phone = request.form['phone']
        user_message = request.form['message']

        msg = Message('New Contact Form Submission',
                        sender = ("USL Contact Form", 'hello@unifiedsl.com'),
                        recipients = ['team@unifiedsl.com,'
                                      ]
                        )
        
        msg.html = render_template('contact_email.html',
                                   first_name = first_name,
                                   last_name = last_name,
                                   lab_name = lab_name,
                                   title = title,
                                   user_email = user_email,
                                   phone = phone,
                                   user_message = user_message,
                                   customer_type = 'Provider')
        try:
            mail.send(msg)

            return render_template('lab_contact_success.html',
                                user = current_user,
                                first_name = first_name,
                                lab_name = lab_name
                                )

        except Exception as e:
            return str(e)

    return render_template('lab_contact.html', 
                           user = current_user)


@contact_bp.route('/lab_contact_question', methods=['GET', 'POST'])
def lab_contact_question():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        lab_name = request.form['lab_name']
        title = request.form['title']
        user_email = request.form['email']
        phone = request.form['phone']
        user_message = request.form['message']

        msg = Message('New Contact Form Submission',
                        sender = ("USL Contact Form", 'hello@unifiedsl.com'),
                        recipients = ['team@unifiedsl.com,'
                                      ]
                        )
        
        msg.html = render_template('contact_email.html',
                                   first_name = first_name,
                                   last_name = last_name,
                                   lab_name = lab_name,
                                   title = title,
                                   user_email = user_email,
                                   phone = phone,
                                   user_message = user_message,
                                   customer_type = 'Provider')
        try:
            mail.send(msg)

            return render_template('lab_contact_success.html',
                                user = current_user,
                                first_name = first_name,
                                lab_name = lab_name
                                )

        except Exception as e:
            return str(e)

    return render_template('lab_contact_question.html', 
                           user = current_user)

@contact_bp.route('/new_test_request', methods=['GET', 'POST'])
def new_test_request():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        user_email = request.form['email']
        phone = request.form['phone']
        user_message = request.form['message']

        msg = Message('New Test Inquiry',
                        sender = ("USL New Test Inquiry", 'hello@unifiedsl.com'),
                        recipients = ['team@unifiedsl.com'
                                      ]
                        )
        
        msg.html = render_template('contact_inquiry_email.html',
                                   first_name = first_name,
                                   last_name = last_name,
                                   user_email = user_email,
                                   phone = phone,
                                   user_message = user_message
                                   )

        mail.send(msg)

        return render_template('contact_success.html', 
                                first_name = first_name,
                                email = user_email, 
                                phone = phone, 
                                message = user_message,
                                user = current_user)


    return render_template('contact_new_test_request.html',
                           user = current_user)