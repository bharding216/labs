from flask import Blueprint, render_template, request, redirect, flash, url_for, \
    session, send_file, jsonify, make_response, Response, send_from_directory, current_app
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from flask_login import login_required, current_user, login_user
from project.models import tests, labs, labs_tests, individuals_login, labs_login, test_requests, \
    email_subscribers, test_results, chat_history
import datetime
from flask_mail import Message
from . import db, mail
from helpers import generate_sitemap, get_lat_long_from_zipcode, distance_calculation
from itsdangerous.url_safe import URLSafeSerializer
import yaml
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous.exc import BadSignature
import shippo
import phonenumbers
from urllib.parse import quote, unquote
import os
import stripe
from markupsafe import Markup
import json
import uuid
import boto3
import requests
from io import BytesIO
from werkzeug.datastructures import Headers

views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_test = request.form.get('selected_test')
        if selected_test is None:
            flash('Please choose a test before submitting the form.')
            return redirect(url_for('views.index'))
        else:
            session['selected_test'] = selected_test

            zipcode = request.form['zipcode']
            if zipcode:
                session['zipcode'] = zipcode

            return redirect(url_for('views.lab_function'))


    else:
        with db.session() as db_session:
            test_names = db_session.query(tests).all()

        return render_template('index.html', 
                               tests = test_names, 
                               user = current_user
                               )

# A custom filter for the homepage test dropdown menu.
@views.app_template_filter('custom_title')
def custom_title(value):
    if value == 'GC-MS':
        return 'GC-MS'
    elif value == 'metals by ICP':
        return 'Metals by ICP'
    else:
        return value.title()


@views.route('/about', methods=['GET'])
def about():
    return render_template('about.html', user = current_user)



@views.route('/labs_about', methods=['GET'])
def labs_about():
    return render_template('labs_about.html', user = current_user)



@views.route('/labs', methods=['GET', 'POST'])
def lab_function():
    if request.method == 'POST':    
        selected_lab_name = request.form['lab_name']
        session['selected_lab_name'] = selected_lab_name

        with db.session() as db_session:
            selected_lab_id = db_session.query(labs.id) \
                .filter(labs.name == selected_lab_name) \
                .scalar()        
            session['selected_lab_id'] = selected_lab_id

        if current_user.is_authenticated:
            return redirect(url_for('views.returning_user_booking'))
        else:
            return redirect(url_for('views.user_info'))

    else:
        selected_test = session.get('selected_test')
        user_zipcode = session.get('zipcode')
        
        with db.session() as db_session:

            # Get the id of the 'selected_test' from the 'tests' table.
            id_in_tests_table = db_session.query(tests.id) \
                .filter(tests.name == selected_test) \
                .scalar()
            
            # Query all the rows in the 'labs_tests' table that match that 'test_id'.
            # This table has lab_ids, prices, and turnaround times for that test_id. 
            test_query_results = db_session.query(
                labs.name, 
                labs_tests.price, 
                labs_tests.turnaround, 
                labs.city, 
                labs.state,
                labs.zip_code) \
                .join(labs_tests, labs_tests.lab_id == labs.id) \
                .filter(labs_tests.test_id == id_in_tests_table) \
                .order_by(labs_tests.price.asc()) \
                .all()


            # Make a list of all zip codes
            zip_code_list = [user_zipcode]
            zip_code_list.extend([result.zip_code for result in test_query_results])

            lat_lng_list = []
            for code in zip_code_list:
                lat_and_lng = get_lat_long_from_zipcode(code)
                lat_lng_list.append(lat_and_lng)

            # Calculate the distance between the coordinates.
            user_latitude, user_longitude = lat_lng_list[0]
            distances = []

            for i in range(1, len(lat_lng_list)):
                lab_latitude, lab_longitude = lat_lng_list[i]
                distance = round(distance_calculation(user_latitude, 
                                                      user_longitude, 
                                                      lab_latitude, 
                                                      lab_longitude
                                                      ))
                distances.append(distance)

        combined_data = zip(test_query_results, distances)

        return render_template('labs.html', 
            selected_test = selected_test, 
            combined_data = combined_data,
            user = current_user
            )




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
        password1 = request.form['password1']
        password2 = request.form['password2']
        sample_description = request.form['sample_description']
        number_of_samples = request.form['sample-number-input']
        extra_requirements = request.form['extra_requirements']

        if password1 != password2:
            flash('Those passwords do not match. Please try again.', category='error')
            selected_lab_id = session.get('selected_lab_id')
            with db.session() as db_session:
                lab_choice = db_session.query(labs).get_or_404(selected_lab_id)
            
            return render_template('new_user_booking.html', 
                                   user = current_user,
                                   lab_choice = lab_choice,
                                   first_name = first_name,
                                   last_name = last_name,
                                   company_name = company_name,
                                   email = email,
                                   phone = phone,
                                   password1 = password1,
                                   password2 = password2,
                                   sample_description = sample_description,
                                   extra_requirements = extra_requirements
                                   )


        session['first_name'] = first_name
        session['sample_description'] = sample_description
        session['extra_requirements'] = extra_requirements
        session['number_of_samples'] = number_of_samples

        # If the phone number string has 10 characters, add '+1' to make it 
        # in the correct format for `phonenumbers`. 
        if len(phone) == 10:
            phone = "+1" + phone
        
        # Try to parse the phone number. 
        # If you can't parse it, then just save the user input as is and move on. 
        try:
            parsed_number = phonenumbers.parse(phone, None)
            formatted_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            phone = formatted_number
        except phonenumbers.NumberParseException:
            pass


        email_exists = individuals_login.query.filter_by(email = email).first()
        if email_exists:
            flash('That email is already in use. Please try another email or log in.', category = 'error')
            selected_lab_id = session.get('selected_lab_id')
            with db.session() as db_session:
                lab_choice = db_session.query(labs).get_or_404(selected_lab_id)
            
            return render_template('new_user_booking.html', 
                                   user = current_user,
                                   lab_choice = lab_choice,
                                   first_name = first_name,
                                   last_name = last_name,
                                   company_name = company_name,
                                   email = email,
                                   phone = phone,
                                   password1 = password1,
                                   password2 = password2,
                                   sample_description = sample_description,
                                   extra_requirements = extra_requirements
                                   )
        else:
            hashed_password = generate_password_hash(password1)
            new_user = individuals_login(
                first_name = first_name, 
                last_name = last_name, 
                password = hashed_password, 
                phone = phone, 
                email = email,
                company_name = company_name,
                type = 'customer'
                )
            
            db.session.add(new_user)
            db.session.commit()

            with db.session() as db_session:
                user = db_session.query(individuals_login).filter_by(email = email).first()
                login_user(user, remember = True)
                session.permanent = True
                session['type'] = 'customer'

            flash('New account successfully created.', category = 'success')
            return redirect(url_for('views.confirmation_new_user'))

    # Handle GET request
    else:
        selected_lab_name = session.get('selected_lab_name')
        with db.session() as db_session:
            selected_lab_id = db_session.query(labs.id) \
                .filter(labs.name == selected_lab_name) \
                .scalar()        
            lab_choice = db_session.query(labs).get_or_404(selected_lab_id)

        return render_template('new_user_booking.html', 
                               user = current_user,
                               lab_choice = lab_choice)



@views.route("/returning_user_login", methods=['GET', 'POST'])
def returning_user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with db.session() as db_session:
            individual_email = db_session.query(individuals_login).filter_by(email = email).first()
        
            if individual_email:
                if check_password_hash(individual_email.password, password):
                    login_user(individual_email, remember=False)
                    session.permanent = True
                    session['type'] = 'customer'
                    flash('Login successful!', category = 'success')
                    return redirect(url_for('views.returning_user_booking'))
                
                else:
                    flash('Incorrect password. Please try again.', category = 'error')
                    return render_template('user_info.html', 
                                            user = current_user, 
                                            email = email)
            else:
                flash('That email is not associated with an account. Please check for typos.', category = 'error')
                return render_template('user_info.html', 
                                        user = current_user, 
                                        email = email)




@views.route("/returning_user_booking", methods=['GET', 'POST'])
@login_required
def returning_user_booking():
    selected_lab_id = session.get('selected_lab_id')
    selected_test = session.get('selected_test')

    with db.session() as db_session:
        lab_choice = db_session.query(labs).get_or_404(selected_lab_id)
        return render_template('returning_user_booking.html', 
                                user = current_user,
                                lab_choice = lab_choice,
                                selected_test = selected_test)



@views.route('/confirmation_new_user', methods=['GET', 'POST'])
@login_required
def confirmation_new_user():
    selected_test = session.get('selected_test')
    first_name = session.get('first_name', None)
    sample_description = session.get('sample_description')
    extra_requirements = session.get('extra_requirements')
    number_of_samples = session.get('number_of_samples')

    selected_lab_name = session.get('selected_lab_name')
    with db.session() as db_session:
        selected_lab_id = db_session.query(labs.id) \
            .filter(labs.name == selected_lab_name) \
            .scalar()
        lab_choice = labs.query.get_or_404(selected_lab_id)
        lab_id = lab_choice.id
        lab_name = lab_choice.name
        lab_email = lab_choice.email

        current_user_id = current_user.id
        user_email = current_user.email
        submitted_datetime = datetime.datetime.now()
        formatted_date = submitted_datetime.strftime("%Y-%m-%d %H:%M:%S")
        date_to_string = str(formatted_date)

        # Save the testing info to the requests table.
        new_request = test_requests(sample_description = sample_description,
                                    number_of_samples = number_of_samples,
                                    extra_requirements = extra_requirements,
                                    test_name = selected_test,
                                    lab_id = lab_id,
                                    approval_status = 'Pending',
                                    requestor_id = current_user_id,
                                    payment_status = 'Not Paid',
                                    transit_status = 'Not Shipped',
                                    datetime_submitted = date_to_string
                                    )

        db.session.add(new_request)
        db.session.commit()

        new_request_id = new_request.request_id

        # Send a confirmation email to the customer.
        msg = Message("We've received your lab testing request",
            sender = ("Unified Science Labs", 'team@unifiedsl.com'),
            recipients = ['team@unifiedsl.com',
                            user_email
                            ]
            )
    
        msg.html = render_template('request_confirmation_email.html',
                                first_name = first_name,
                                lab_name = lab_name,
                                selected_test = selected_test,
                                number_of_samples = number_of_samples,
                                sample_description = sample_description,
                                extra_requirements = extra_requirements,
                                approval_status = 'Pending',
                                new_request_id = new_request_id
                                )

        mail.send(msg)

        # Send an email to the lab notifying them of the new request.
        msg = Message("You've received a new request",
            sender = ("Unified Science Labs", 'team@unifiedsl.com'),
            recipients = ['team@unifiedsl.com',
                            lab_email
                            ]
            )
    
        msg.html = render_template('lab_request_email_notification.html',
                                lab_name = lab_name,
                                selected_test = selected_test,
                                number_of_samples = number_of_samples,
                                sample_description = sample_description,
                                extra_requirements = extra_requirements,
                                approval_status = 'Pending',
                                new_request_id = new_request_id
                                )

        mail.send(msg)


        # Lastly, render the 'request confirmation' page. 
        return render_template('confirmation.html', 
                                selected_test = selected_test,
                                first_name = first_name,
                                lab_choice = lab_choice,
                                user = current_user,
                                number_of_samples = number_of_samples
                                )


@views.route('/confirmation_returning_user', methods=['GET', 'POST'])
@login_required
def confirmation_returning_user():
    if request.method == 'POST':
        sample_description = request.form['sample_description']
        extra_requirements = request.form['extra_requirements']
        number_of_samples = request.form['sample-number-input']

        selected_test = session.get('selected_test')
        selected_lab_id = session.get('selected_lab_id')
        
        with db.session() as db_session:
            lab_choice = db_session.query(labs).get_or_404(selected_lab_id)
            lab_id = lab_choice.id
            lab_name = lab_choice.name
            lab_email = lab_choice.email

            # May not need this code block. On the HTML page, you could probably just use 
            # {{ user.first_name }} to get the first name (assuming you pass 'user = current_user'
            # to the HTML template).
            current_user_id = current_user.id
            logged_in_user = db_session.query(individuals_login).filter_by(id = current_user_id).first()
            first_name = logged_in_user.first_name
            user_email = logged_in_user.email

            submitted_datetime = datetime.datetime.now()
            formatted_date = submitted_datetime.strftime("%Y-%m-%d %H:%M:%S")
            date_to_string = str(formatted_date)

            # Save the testing info to the test_requests db table.
            new_request = test_requests(sample_description = sample_description,
                                        number_of_samples = number_of_samples,
                                        extra_requirements = extra_requirements,
                                        test_name = selected_test,
                                        approval_status = 'Pending',
                                        lab_id = lab_id,
                                        requestor_id = current_user_id,
                                        payment_status = 'Not Paid',
                                        transit_status = 'Not Shipped',
                                        datetime_submitted = date_to_string
                                        )


            db.session.add(new_request)
            db.session.commit()

            new_request_id = new_request.request_id

            # Send a confirmation email to the customer.
            msg = Message("We've received your lab testing request",
                sender = ("Unified Science Labs", 'team@unifiedsl.com'),
                recipients = ['team@unifiedsl.com',
                              user_email
                              ]
                )
        
            msg.html = render_template('request_confirmation_email.html',
                                    first_name = first_name,
                                    lab_name = lab_name,
                                    selected_test = selected_test,
                                    number_of_samples = number_of_samples,
                                    sample_description = sample_description,
                                    extra_requirements = extra_requirements,
                                    approval_status = 'Pending',
                                    new_request_id = new_request_id
                                    )

            mail.send(msg)

            # Send an email to the lab notifying them of the new request.
            msg = Message("You've received a new request",
                sender = ("Unified Science Labs", 'team@unifiedsl.com'),
                recipients = ['team@unifiedsl.com',
                                lab_email
                                ]
                )
        
            msg.html = render_template('lab_request_email_notification.html',
                                    lab_name = lab_name,
                                    selected_test = selected_test,
                                    number_of_samples = number_of_samples,
                                    sample_description = sample_description,
                                    extra_requirements = extra_requirements,
                                    approval_status = 'Pending',
                                    new_request_id = new_request_id
                                    )

            mail.send(msg)



            # Lastly, render the 'request confirmation' page. 
            return render_template('confirmation.html', 
                                selected_test = selected_test,
                                first_name = first_name,
                                lab_choice = lab_choice,
                                user = current_user,
                                number_of_samples = number_of_samples
                                )



@views.route('/new_email_subscriber', methods=['GET', 'POST'])
@login_required
def new_email_subscriber():
    if request.method == 'POST':
        subscriber_email_input = request.form['subscriber_email_input']

        email_to_add = email_subscribers(email = subscriber_email_input)
        with db.session() as db_session:
            db_session.add(email_to_add)
            db_session.commit()

            flash("You're in! You should receive a confirmation email shortly.", 'success')
            return render_template('index.html', 
                                    user = current_user
                                    )



@views.route('/lab_requests', methods=['GET', 'POST'])
@login_required
def lab_requests():
    with db.session() as db_session:
        lab_object = current_user.labs
        lab_id = lab_object.id

        lab_requests = db_session.query(test_requests) \
                                .filter_by(lab_id = lab_id) \
                                .order_by(test_requests.datetime_submitted.desc()) \
                                .all() 

        return render_template('lab_requests.html', 
                                user = current_user,
                                lab_requests = lab_requests)





@views.route('/submit_details', methods = ['GET', 'POST'])
@login_required
def submit_details():
    if request.method == 'POST':
        data = request.get_json()

        # This code accesses the first item in the list (my_list[0]), 
        # which is a dictionary with a single key-value pair ({'id': '7'}). 
        # Then, it calls the values() method on this dictionary to retrieve 
        # a list of its values, which in this case is ['7']. Finally, it 
        # uses indexing to access the first (and only) value in this list 
        # (list(my_list[0].values())[0]), which is the string "7". This 
        # value is then assigned to the variable value and printed out.
        request_id_from_ajax = list(data[0].values())[0]
        new_details = list(data[2].values())[0]
        status = 'Need more details'

        with db.session() as db_session:
            db_session.query(test_requests) \
                .filter_by(request_id = request_id_from_ajax) \
                .update({'approval_status': status,
                         'labs_response': new_details
                         })
            db_session.commit()

            request_object = db_session.query(test_requests) \
                                .filter_by(request_id = request_id_from_ajax) \
                                .first()
            if request_object:    
                selected_test = request_object.test_name
                number_of_samples = request_object.number_of_samples
                sample_description = request_object.sample_description
                extra_requirements = request_object.extra_requirements
                lab = db_session.query(labs) \
                        .filter_by(id = request_object.lab_id) \
                        .first()
                lab_name = lab.name

                individual_id = request_object.requestor_id
                individual = db_session.query(individuals_login) \
                                .filter_by(id = individual_id).first()
                first_name = individual.first_name
                user_email = individual.email


        # Send an email to the customer letting them know 
        # that the provider is requesting additional details.
        msg = Message("Order On Hold: Additional Details Needed",
            sender = ("Unified Science Labs", 'team@unifiedsl.com'),
            recipients = ['team@unifiedsl.com',
                            user_email
                            ]
            )
    
        msg.html = render_template('request_status_changed_email.html',
                                first_name = first_name,
                                lab_name = lab_name,
                                selected_test = selected_test,
                                number_of_samples = number_of_samples,
                                sample_description = sample_description,
                                extra_requirements = extra_requirements,
                                approval_status = 'Need more details',
                                new_details = new_details,
                                request_id = request_id_from_ajax
                                )

        mail.send(msg)

        return data
    





@views.route('/manage_results/<int:request_id>', methods = ['GET', 'POST'])
@login_required
def manage_results(request_id):
    lab_object = current_user.labs
    lab_id = lab_object.id

    test_request = test_requests.query.filter_by(request_id=request_id).first()
    test_name = test_request.test_name

    with db.session() as db_session:
        test_results_query = db_session.query(test_results) \
                                       .filter_by(request_id=request_id, lab_id=lab_id) \
                                       .all()

        return render_template('manage_results.html',
                            user = current_user,
                            test_name = test_name,
                            request_id = request_id,
                            test_results_query = test_results_query)



@views.route('/upload', methods = ['GET', 'POST'])
@login_required
def upload():

    files = request.files.getlist('file[]')
    now = datetime.datetime.now()
    date_time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    secure_date_time_stamp = secure_filename(date_time_stamp)
    request_id = request.form['request_id']
    
    lab_object = current_user.labs
    lab_id = lab_object.id

    # Configure S3 credentials
    s3 = boto3.client('s3', region_name='us-east-1',
                    aws_access_key_id=os.getenv('s3_access_key_id'),
                    aws_secret_access_key=os.getenv('s3_secret_access_key'))
    
    # Set the name of your S3 bucket
    S3_BUCKET = 'usl-results-bucket'

    for file in files:
        s3_filename = f"{secure_date_time_stamp}_{secure_filename(file.filename)}"
        s3.upload_fileobj(file, S3_BUCKET, s3_filename)

        new_test_results_record = {
            'filename': file.filename,
            'request_id': request_id,
            'date_time_stamp': date_time_stamp,
            'lab_id': lab_id
        }

        with db.session() as db_session:
            new_results = test_results(**new_test_results_record)
            db_session.add(new_results)
            db_session.commit()

    flash('File(s) uploaded successfully', 'success')
    return redirect(url_for('views.view_request_details', request_id=request_id))




@views.route('/download', methods = ['GET', 'POST'])
@login_required
def download():
    filename = request.form['filename']
    date_time_stamp = request.form['date_time_stamp']
    secure_date_time_stamp = secure_filename(date_time_stamp)

    s3_filename = f"{secure_date_time_stamp}_{secure_filename(filename)}"

    s3 = boto3.client('s3', region_name='us-east-1',
                    aws_access_key_id=os.getenv('s3_access_key_id'),
                    aws_secret_access_key=os.getenv('s3_secret_access_key'))

    S3_BUCKET = 'usl-results-bucket'

    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': S3_BUCKET,
            'Key': s3_filename
        },
        ExpiresIn=3600
    )

    response = requests.get(url)

    download_filename = secure_filename(filename)

    headers = Headers()
    headers.add('Content-Disposition', 'attachment', filename=download_filename)
    response.headers['Content-Disposition'] = 'attachment; filename=' + download_filename

    return Response(BytesIO(response.content), headers=headers)




@views.route('/delete', methods = ['GET', 'POST'])
@login_required
def delete():
    request_id = request.form['request_id']
    filename = request.form['filename']
    date_time_stamp = request.form['date_time_stamp']
    secure_date_time_stamp = secure_filename(date_time_stamp)

    s3_filename = f"{secure_date_time_stamp}_{secure_filename(filename)}"

    s3 = boto3.client('s3', region_name='us-east-1',
                    aws_access_key_id=os.getenv('s3_access_key_id'),
                    aws_secret_access_key=os.getenv('s3_secret_access_key'))

    S3_BUCKET = 'usl-results-bucket'

    s3.delete_object(Bucket=S3_BUCKET, Key=s3_filename)

    with db.session() as db_session:
        obj = db_session.query(test_results).filter_by(filename=filename).first()
        db_session.delete(obj)
        db_session.commit()

    flash('File deleted successfully', 'success')
    return redirect(url_for('views.view_request_details', request_id=request_id))










@views.route("/user_requests", methods=['GET', 'POST'])
@login_required
def user_requests():
    if request.method == 'POST':
        # If the user wants to get a shipping label with their test.
        lab_name = request.form['lab_name']
        test_name = request.form['test_name']
        number_of_samples = request.form['number_of_samples']
        request_id = request.form['request_id']

        session['lab_name_for_shipping_label'] = lab_name
        session['test_name_for_shipping_label'] = test_name
        session['number_of_samples_for_shipping_label'] = number_of_samples
        session['request_id'] = request_id

        return redirect(url_for('views.shipping'))
       
    else:   
        with db.session() as db_session:
            my_requests = db_session.query(test_requests, labs.name) \
                .join(labs, test_requests.lab_id == labs.id) \
                .filter(test_requests.requestor_id == current_user.id) \
                .order_by(test_requests.datetime_submitted.desc()) \
                .all()
            
            return render_template('user_requests.html', 
                                    user = current_user,
                                    my_requests = my_requests
                                    )



@views.route('/view_request_details/<int:request_id>', methods=['GET', 'POST'])
@login_required
def view_request_details(request_id):
    with db.session() as db_session:
        request_object = db_session.query(test_requests) \
            .filter_by(request_id = request_id) \
            .order_by(test_requests.datetime_submitted.desc()) \
            .first()

        lab_record = labs.query.filter_by(id=request_object.lab_id).first()
        lab_name = lab_record.name

        test_result_records = db_session.query(test_results) \
            .filter_by(request_id = request_id) \
            .order_by(test_results.date_time_stamp.desc()) \
            .all()

        chat_query = db.session.query(chat_history).\
            join(test_requests, (chat_history.lab_id == test_requests.lab_id) & 
                                (chat_history.customer_id == test_requests.requestor_id)).\
            options(joinedload(chat_history.customer), joinedload(chat_history.lab)).\
            filter(test_requests.request_id == request_id)

        chat_history_records = chat_query.all()

        return render_template('view_request_details.html',
                            user = current_user,
                            request_object = request_object,
                            chat_history_records = chat_history_records,
                            test_result_records = test_result_records,
                            lab_name = lab_name
                            )



@views.route('/post_chat_message', methods=['GET', 'POST'])
@login_required
def post_chat_message():
    message = request.form['message']
    request_id = request.form['request_id']
    now = datetime.datetime.now()
    date_time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")

    with db.session() as db_session:
        request_object = db_session.query(test_requests) \
            .filter_by(request_id = request_id) \
            .first()

        lab_id = request_object.lab_id
        customer_id = request_object.requestor_id

        if session['type'] == 'customer':
            author_type = 'customer'
        elif session['type'] == 'lab':
            author_type = 'lab'
        else:
            return 'Error: Session user_type not set'

        new_comment = chat_history(author_type = author_type, 
                                datetime_submitted = date_time_stamp, 
                                comment = message, 
                                lab_id = lab_id,
                                customer_id = customer_id
                                )
        
        db.session.add(new_comment)
        db.session.commit()

        flash('New comment successfully added!', category='success')

        return redirect(url_for('views.view_request_details', 
                        request_id = request_id))



@views.route('/change_request_status/<int:request_id>', methods=['GET', 'POST'])
@login_required
def change_request_status(request_id):
    if request.method == 'POST':
        new_status = request.form['status-dropdown']

        with db.session() as db_session:
            request_object = db_session.query(test_requests) \
                .filter_by(request_id = request_id) \
                .first()

            request_object.approval_status = new_status
            db_session.commit()

            flash('Request status updated!', category='success')
            return redirect(url_for('views.view_request_details', request_id=request_id))



@views.route("/user_more_details", methods=['GET', 'POST'])
@login_required
def user_more_details():
    if request.method == 'POST':
        request_id = request.form['request_id']
        labs_response = request.form['labs_response']
        extra_requirements = request.form['extra_requirements']
        lab_name = request.form['lab_name']
        return render_template('user_more_details.html',
                               user = current_user,
                               labs_response = labs_response,
                               extra_requirements = extra_requirements,
                               lab_name = lab_name,
                               request_id = request_id)


@views.route("/update_request", methods=['GET', 'POST'])
@login_required
def update_request():
    if request.method == 'POST':
        request_id = request.form['request_id']
        extra_requirements = request.form['extra_requirements']

        with db.session() as db_session:
            db_session.query(test_requests) \
                .filter_by(request_id = request_id) \
                .update({'extra_requirements': extra_requirements})
            db_session.commit()

            request_object = db_session.query(test_requests) \
                                .filter_by(request_id = request_id) \
                                .first()
            if request_object:    
                selected_test = request_object.test_name
                number_of_samples = request_object.number_of_samples
                sample_description = request_object.sample_description
                extra_requirements = request_object.extra_requirements
                labs_response = request_object.labs_response
                lab = db_session.query(labs) \
                        .filter_by(id = request_object.lab_id) \
                        .first()
                lab_name = lab.name
                lab_email = lab.email

                individual_id = request_object.requestor_id
                individual = db_session.query(individuals_login) \
                                .filter_by(id = individual_id).first()
                first_name = individual.first_name
                user_email = individual.email


        # Send an email to the customer with their updated request info.
        msg = Message("New Details Added To Request",
            sender = ("Unified Science Labs", 'team@unifiedsl.com'),
            recipients = ['team@unifiedsl.com',
                            user_email
                            ]
            )
    
        msg.html = render_template('request_details_updated_email_to_customer.html',
                                    first_name = first_name,
                                    lab_name = lab_name,
                                    selected_test = selected_test,
                                    number_of_samples = number_of_samples,
                                    sample_description = sample_description,
                                    extra_requirements = extra_requirements,
                                    approval_status = 'Need more details',
                                    new_details = extra_requirements,
                                    request_id = request_id,
                                    labs_response = labs_response
                                    )

        mail.send(msg)

        # Send an email to the lab notifying them of the new request.
        msg = Message("A Request Has Been Updated",
            sender = ("Unified Science Labs", 'team@unifiedsl.com'),
            recipients = ['team@unifiedsl.com',
                            lab_email
                            ]
            )
    
        msg.html = render_template('request_details_updated_email_to_lab.html',
                                    lab_name = lab_name,
                                    selected_test = selected_test,
                                    number_of_samples = number_of_samples,
                                    sample_description = sample_description,
                                    extra_requirements = extra_requirements,
                                    approval_status = 'Pending',
                                    request_id = request_id,
                                    labs_response = labs_response
                                    )

        mail.send(msg)


        flash("Your request has been successfully updated! We've notified \
              the lab, and we will get back to you via email shortly.", 'success')

        return redirect(url_for('views.user_requests'))


@views.route("/customer_settings", methods=['GET', 'POST'])
@login_required
def customer_settings():
    if request.method == 'POST':
        # The name of the category you are updating.
        field_name = request.form['field_name']

        return render_template('update_customer.html',
                            user = current_user,
                            field_name = field_name)

                

    return render_template('customer_settings.html', 
                            user = current_user
                            )

@views.route("/provider_settings", methods=['GET', 'POST'])
@login_required
def provider_settings():
    if request.method == 'POST':
        # Check if the user is updating their profile info.
        if request.form['type'] == "info":
            lab_id = request.form['id']
            field_name = request.form['field_name']

            with db.session() as db_session:
                lab_object = db_session.query(labs).get(lab_id)

                if lab_object is not None:
                    return render_template('update_lab.html',
                                        user = current_user,
                                        lab_object = lab_object,
                                        field_name = field_name)
                else:
                    flash('Lab not found.', 'error')
                    return redirect(url_for('views.provider_settings'))
        
        # Check if the user is updating their test offering info.
        if request.form['type'] == "tests_prices":
            lab_id = request.form['id']
            test_name = request.form['test_name']
            test_name_encoded = quote(test_name)
            test_price = request.form['test_price']
            test_turnaround = request.form['test_turnaround']
            return render_template('update_prices.html',
                                   test_name_encoded = test_name_encoded,
                                   test_name = test_name,
                                   test_price = test_price,
                                   user = current_user,
                                   lab_id = lab_id,
                                   test_turnaround = test_turnaround)

    current_user_lab_id = current_user.lab_id

    with db.session() as db_session:
        logged_in_lab = db_session.query(labs).filter_by(id = current_user_lab_id).first()

        tests_and_pricing = db_session.query(tests.name, labs_tests.price, labs_tests.turnaround).\
                                join(labs_tests, tests.id == labs_tests.test_id).\
                                filter(labs_tests.lab_id == current_user_lab_id).\
                                order_by(tests.name.asc()).\
                                all()


    return render_template('provider_settings.html', 
                            user = current_user,
                            lab = logged_in_lab,
                            tests_and_pricing = tests_and_pricing
                            )


@views.route("/add_new_test", methods=['GET', 'POST'])
@login_required
def add_new_test():
    if request.method == 'POST':
        current_user_lab_id = current_user.lab_id
        test_name = request.form['test_name']
        test_price = request.form['test_price']
        turnaround = request.form['turnaround']
        test_input_source = request.form['test_input_source']


        with db.session() as db_session:

            if test_input_source == 'text_input':
                # If the user typed in a new test name, then add
                # it to the 'tests' table. 
                new_test = tests(name = test_name)
                db_session.add(new_test)
                db_session.commit()

            # You're going to create a list of the tests that are currently offered by
            # the 'logged in lab'.
            joined_data = db_session.query(labs_tests, tests).join(tests, labs_tests.test_id == tests.id)
            tests_for_lab = joined_data.filter(labs_tests.lab_id == current_user_lab_id)
            test_names = [test.name for _, test in tests_for_lab]

            # Check if the test that the lab is trying to add is already listed.
            if test_name in test_names:
                prev_page_url = url_for('views.provider_settings')
                flash(Markup(f'That test is already in your offerings. Please edit the \
                      test parameters on the <a href="{prev_page_url}">previous page</a>.'), 'error')
                
                test_names = db_session.query(tests.name).order_by(tests.name).all()
                test_names = [name[0] for name in test_names]

                return render_template('add_new_test.html',
                                       user = current_user,
                                       test_names = test_names
                                       )

            test_to_add = tests.query.filter_by(name = test_name).first()
            if test_to_add:
                test_id = test_to_add.id

            # Add the test to the labs_tests table for the 'logged in lab'.
            new_lab_test = labs_tests(lab_id = current_user_lab_id, 
                                    test_id = test_id,
                                    price = test_price,
                                    turnaround = turnaround)

            db_session.add(new_lab_test)
            db_session.commit()
        
        flash('New test successfully added!', 'success')
        return redirect(url_for('views.provider_settings'))

    with db.session() as db_session:
        test_names = db_session.query(tests.name).order_by(tests.name).all()
        # Convert list of tuples to list of strings:
        test_names = [name[0] for name in test_names]

    return render_template('add_new_test.html', 
                            user = current_user,
                            test_names = test_names
                            )


@views.route("/update_prices/<int:id>/<path:test_name>", methods=['GET', 'POST'])
@login_required
def update_prices(id, test_name):

    new_price = request.form.get('test_price')
    new_turnaround = request.form.get('test_turnaround')
    test_name = unquote(test_name)
    
    with db.session() as db_session:
        test_object = db_session.query(tests).filter_by(name = test_name).first()
        lab_object = db_session.query(labs).get(id)

        labs_tests_object = db_session.query(labs_tests) \
            .filter_by(lab_id = lab_object.id, test_id = test_object.id) \
            .first()
        
        labs_tests_object.price = new_price
        labs_tests_object.turnaround = new_turnaround

        db.session.add(labs_tests_object)
        db.session.commit()

    flash('Settings updated for ' + test_name +'.', 'success')

    return redirect(url_for('views.provider_settings'))




@views.route("/update_customer/<string:field_name>", methods=['GET', 'POST'])
@login_required
def update_customer(field_name):
    if request.method == 'POST':
        new_value = request.form[field_name]

        if field_name == 'password':
            password2 = request.form['password2']
            if new_value == password2:
                new_value = generate_password_hash(new_value)
                current_user.password = new_value

                with db.session() as db_session:
                    db_session.add(current_user)
                    db_session.commit()

                    flash('Password successfully updated!', 'success')
                    return redirect(url_for('views.customer_settings'))

            else:
                flash('Those password do not match, please try again', 'error')
                return render_template('update_customer.html',
                                    user = current_user,
                                    field_name = field_name)



        setattr(current_user, field_name, new_value)
        with db.session() as db_session:
            db_session.commit()
            flash('Your settings have been successfully updated!', 'success')
            return redirect(url_for('views.customer_settings'))
        



@views.route("/update_lab/<int:id>/<string:field_name>", methods=['GET', 'POST'])
@login_required
def update_lab(id, field_name):
    with db.session() as db_session:
        lab_object = db_session.query(labs).get(id)
        new_value = request.form[field_name]

        if field_name == 'password':
            password2 = request.form['password2']
            if new_value == password2:
                new_value = generate_password_hash(new_value)

                lab_login_object = db_session.query(labs_login).filter_by(lab_id=id).first()
                lab_login_object.password = new_value

                db_session.add(lab_login_object)
                db_session.commit()

                flash('Password successfully updated!', 'success')
                return redirect(url_for('views.provider_settings'))

            else:
                flash('Those password do not match, please try again', 'error')
                return render_template('update_lab.html',
                                    user = current_user,
                                    lab_object = lab_object,
                                    field_name = field_name)

        # The setattr() function is a built-in Python function that takes 
        # three arguments: an object, a string indicating the name of 
        # an attribute, and a new value for the attribute.  
        setattr(lab_object, field_name, new_value)
        
        db_session.commit()
        flash('Your settings have been successfully updated!', 'success')

        return redirect(url_for('views.provider_settings'))



@views.route('/shipping', methods=['GET', 'POST'])
@login_required
def shipping():
    if request.method == 'POST':
        shippo.config.api_key = os.getenv('shippo_api_key')

        street1 = request.form['from_address_1']
        street2 = request.form['from_address_2']
        city = request.form['city']
        state = request.form['state']
        zip = request.form['zip']

        user = individuals_login.query.filter_by(id=current_user.id).first()
        first_name = user.first_name
        last_name = user.last_name
        full_name = first_name + last_name
        phone = user.phone
        email = user.email

        address_from = {
            "name": full_name,
            "street1": street1,
            "street2": street2,
            "city": city,
            "state": state,
            "zip": zip,
            "country": "US",
            "phone": phone,
            "email": email
            }

        lab_name = session.get('lab_name_for_shipping_label')
        lab = labs.query.filter_by(name = lab_name).first()
        formatted_phone = f"{lab.phone[:2]} {lab.phone[2:5]} {lab.phone[5:8]} {lab.phone[8:]}"


        address_to = {
            "name": lab.name,
            "street1": lab.street_address_1,
            "street2": lab.street_address_2,
            "city": lab.city,
            "state": lab.state,
            "zip": lab.zip_code,
            "country": lab.country,
            "phone": formatted_phone
        }

        length = request.form['length']
        width = request.form['width']
        height = request.form['height']
        weight = request.form['weight']

        parcel = {
            "length": length,
            "width": width,
            "height": height,
            "distance_unit": 'in',
            "weight": weight,
            "mass_unit": 'lb'
            }

        shipment = shippo.Shipment.create(
            address_from = address_from,
            address_to = address_to,
            parcels = [parcel],
            asynchronous = False
            )

        rates = shipment.rates

        # Set your shipping label markup here:
        for rate in rates:
            rate.amount = round(float(rate.amount) * 1.15, 2)

        sorted_rates = sorted(rates, key=lambda resp: float(resp['amount']))
     
        lab_name = session.get('lab_name_for_shipping_label')
        test_name = session.get('test_name_for_shipping_label')

        return render_template('shipping_rates.html',
                               user = current_user,
                               rates = sorted_rates,
                               lab_name = lab_name,
                               test_name = test_name
                               )


    lab_name = session.get('lab_name_for_shipping_label')
    lab = labs.query.filter_by(name = lab_name).first()

    return render_template('shipping.html', 
                           user = current_user,
                           lab = lab
                           )














@views.route('/checkout/<int:lab_id>/<string:test_name>', methods=['GET', 'POST'])
@login_required
def checkout(lab_id, test_name):
    if request.method == 'POST':
        test_record = tests.query.filter_by(name = test_name).first()

        row_in_labs_tests = labs_tests.query.filter_by(lab_id = lab_id, 
                                                       test_id = test_record.id) \
                                                       .first()
        price = row_in_labs_tests.price
        stripe_price = int(price * 100)

        stripe.api_key = os.getenv('stripe_secret_key')

        # Check if the user is getting a shipping label
        label_purchase = request.form['label_purchase']

        if label_purchase == 'yes':
            selected_rate_object = json.loads(request.form.get('selected_rate'))
            session['selected_rate_object'] = selected_rate_object
            number_of_samples = session.get('number_of_samples_for_shipping_label')

            stripe_session = stripe.checkout.Session.create(
                payment_method_types = ['card'],
                invoice_creation={"enabled": True}, # https://stripe.com/docs/payments/checkout/post-payment-invoices
                line_items = [
                    {'price_data': {
                            'currency': 'usd',
                            'unit_amount': stripe_price,
                            'product_data': {
                                'name': test_record.name,
                                },
                            }, 'quantity': number_of_samples,
                        },

                    {'price_data': {
                            'currency': 'usd',
                            'unit_amount': int(float(selected_rate_object['amount']) * 100),
                            'product_data': {
                                'name': 'Shipping label - ' + selected_rate_object['provider'],
                                },
                            }, 'quantity': 1,
                        }
                ],
                mode = 'payment',
                success_url = url_for('views.success',
                                      _external = True, 
                                      label_purchase = label_purchase
                                      ),
                cancel_url = url_for('views.index', 
                                     _external = True
                                     )
            )

            session['stripe_session'] = stripe_session
            return redirect(stripe_session.url) # Goes to 'views.success'

        
        else: # If the user is not purchasing a label.
            number_of_samples = request.form['number_of_samples']
            request_id = request.form['request_id']
            session['request_id'] = request_id


            stripe_session = stripe.checkout.Session.create(
                payment_method_types = ['card'],
                invoice_creation={"enabled": True}, # https://stripe.com/docs/payments/checkout/post-payment-invoices
                line_items = [{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': stripe_price,
                        'product_data': {
                            'name': test_record.name,
                        },
                    },
                    'quantity': number_of_samples,
                }],
                mode = 'payment',
                success_url = url_for('views.success', _external = True),
                cancel_url = url_for('views.index', _external = True)
            )
            session['stripe_session'] = stripe_session

            return redirect(stripe_session.url) # Goes to views.success




@views.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    stripe.api_key = os.getenv('stripe_secret_key')
    stripe_signing_secret = os.getenv('stripe_signing_secret')
    payload = request.data.decode('utf-8')
    sig_header = request.headers.get('Stripe-Signature')
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_signing_secret
        )
    except ValueError as e:
        return Response(status=400)

    if event and event['type'] == 'payment_intent.succeeded':
        return jsonify(success=True)


@views.route('/order/success')
@login_required
def success():
    stripe.api_key = os.getenv('stripe_secret_key')
    stripe_session = session.get('stripe_session')
    stripe.checkout.Session.retrieve(stripe_session.id)
    # The docs: https://stripe.com/docs/api/checkout/sessions/retrieve

    label_purchase = request.args.get('label_purchase')
    if label_purchase == 'yes':
        selected_rate_object = session.get('selected_rate_object')
        
        shippo.config.api_key = os.getenv('shippo_api_key')
        transaction = shippo.Transaction.create(rate=selected_rate_object['object_id'], 
                                                asynchronous=False
                                                )

        if transaction.status == "SUCCESS":
            request_id = session.get('request_id')

            with db.session() as db_session:
                db_session.query(test_requests) \
                    .filter_by(request_id = request_id) \
                    .update({'payment_status': 'Paid',
                            'transit_status': 'In Transit'})
                db_session.commit()

                request_object = db_session.query(test_requests) \
                                    .filter_by(request_id = request_id) \
                                    .first()
                if request_object:    
                    selected_test = request_object.test_name
                    number_of_samples = request_object.number_of_samples
                    sample_description = request_object.sample_description
                    extra_requirements = request_object.extra_requirements
                    payment_status = request_object.payment_status
                    approval_status = request_object.approval_status
                    lab = db_session.query(labs) \
                            .filter_by(id = request_object.lab_id) \
                            .first()
                    lab_name = lab.name
                    lab_email = lab.email

                msg = Message("Payment Completed",
                    sender = ("Unified Science Labs", 'hello@unifiedsl.com'),
                    recipients = ['team@unifiedsl.com']
                    )
            
                msg.html = render_template('successful_payment_email_to_lab.html',
                                            lab_name = lab_name,
                                            selected_test = selected_test,
                                            number_of_samples = number_of_samples,
                                            sample_description = sample_description,
                                            extra_requirements = extra_requirements,
                                            approval_status = approval_status,
                                            payment_status = payment_status,
                                            request_id = request_id
                                            )
                mail.send(msg)

                return render_template('order_success.html',
                                        user = current_user,
                                        transaction = transaction,
                                        label_purchase = label_purchase
                                        )
        else:
            error_message_list = []
            for message in transaction.messages:
                error_message_list.append(message)
                return render_template('order_error.html', 
                                    user = current_user,
                                    transaction = transaction,
                                    error_message_list = error_message_list)

    else: # If the user chose not to buy a label, just take them to the success page.
        request_id = session.get('request_id')

        with db.session() as db_session:
            db_session.query(test_requests) \
                .filter_by(request_id = request_id) \
                .update({'payment_status': 'Paid'})
            db_session.commit()

            request_object = db_session.query(test_requests) \
                                .filter_by(request_id = request_id) \
                                .first()
            if request_object:    
                selected_test = request_object.test_name
                number_of_samples = request_object.number_of_samples
                sample_description = request_object.sample_description
                extra_requirements = request_object.extra_requirements
                payment_status = request_object.payment_status
                approval_status = request_object.approval_status
                lab = db_session.query(labs) \
                        .filter_by(id = request_object.lab_id) \
                        .first()
                lab_name = lab.name
                lab_email = lab.email

                msg = Message("Payment Completed",
                    sender = ("Unified Science Labs", 'team@unifiedsl.com'),
                    recipients = ['team@unifiedsl.com',
                                    lab_email
                                    ]
                    )
            
                msg.html = render_template('successful_payment_email_to_lab.html',
                                            lab_name = lab_name,
                                            selected_test = selected_test,
                                            number_of_samples = number_of_samples,
                                            sample_description = sample_description,
                                            extra_requirements = extra_requirements,
                                            approval_status = approval_status,
                                            payment_status = payment_status,
                                            request_id = request_id
                                            )
                mail.send(msg)

                return render_template('order_success.html',
                                        user = current_user
                                        )












@views.route("/privacy_policy", methods=['GET', 'POST'])
def privacy_policy():
    return render_template('privacy_policy.html', 
                            user = current_user
                            )



@views.route("/reset_password_request/<string:user_type>", methods=['GET', 'POST'])
def reset_password_request(user_type):
    if request.method == "POST":
        email = request.form.get("email")
        
        if user_type == 'individual':
            user = individuals_login.query.filter_by(email=email).first()
        else: # user_type is 'lab'
            user = labs_login.query.filter_by(email=email).first()

        if user:
            current_time = datetime.datetime.now().time()
            current_time_str = current_time.strftime('%H:%M:%S')

            s = URLSafeSerializer(os.getenv('secret_key'))

            # 'dumps' takes a list as input and serializes it into a string representation.
            # This returns a string representation of the data - encoded using your secret key.
            token = s.dumps([email, current_time_str])

            reset_password_url = url_for('views.reset_password', 
                                          token = token, 
                                          _external=True
                                          )

            msg = Message('Password Reset Request', 
                sender = ("Unified Science Labs", 'hello@unifiedsl.com'),
                recipients = [email],
                body=f'Reset your password by visiting the following link: {reset_password_url}')

            mail.send(msg) 
            flash('Success! We sent you an email containing a link where you can reset your password.', category = 'success')
            return redirect(url_for('views.index'))

        else:
            flash('That email does not exist in our system. Please try again.', category = 'error')
            return redirect(url_for('views.reset_password_request',
                                     user_type = user_type,
                                     user = current_user
                                     )
                            )
    
    else:
        return render_template("reset_password_form.html", 
                               user_type = user_type,
                               user = current_user)





@views.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":

        s = URLSafeSerializer(os.getenv('secret_key'))
        try: 
            # loads => take in a serialized string and generate the original list of string inputs.
            # The first element in the list is the user's email.
            user_email_from_token = (s.loads(token))[0]
        except BadSignature:
            flash('You do not have permission to change the password for this email. Please contact us if you continue to have issues.', category = 'error')
            return redirect(url_for('views.reset_password', 
                                    token = token))

        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash('Those passwords do not match. Please try again.', category='error')
            return redirect(url_for('views.reset_password', 
                                    token = token))

        hashed_password = generate_password_hash(new_password)
        
        user = individuals_login.query.filter_by(email = user_email_from_token).first()
        if user is None: # Then it must have been a lab requesting a new password
            user = labs_login.query.filter_by(email = user_email_from_token).first()

        user.password = hashed_password
        db.session.commit()

        flash('Your password has been successfully updated! Please login.', category = 'success')
        return redirect(url_for('views.index'))

    else:
        return render_template("reset_password.html", 
                               user = current_user, 
                               token = token
                               )





@views.route('/terms')
def terms():
    return render_template('terms.html',
                           user = current_user)



@views.route('/sitemap.xml', methods=['GET'])
def sitemap():
    sitemap_xml = generate_sitemap()
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@views.route("/robots.txt")
def static_from_root():
    views.static_folder = 'static'
    return send_from_directory(views.static_folder, request.path[1:])