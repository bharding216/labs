from flask import Blueprint, render_template, request, redirect, flash, url_for, \
    session, send_file, jsonify, make_response, Response, send_from_directory
from sqlalchemy import func
from flask_login import login_required, current_user, login_user
from project.models import tests, labs, labs_tests, individuals_login, labs_login, test_requests
import datetime
from flask_mail import Message
from . import db, mail
from helpers import generate_sitemap, get_lat_long_from_zipcode, distance_calculation
from itsdangerous.url_safe import URLSafeSerializer
import yaml
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous.exc import BadSignature
import shippo
import phonenumbers
from urllib.parse import quote, unquote
import os
import stripe
from markupsafe import Markup




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
        password = request.form['password']
        sample_description = request.form['sample_description']
        extra_requirements = request.form['extra_requirements']

        session['first_name'] = first_name
        session['sample_description'] = sample_description
        session['extra_requirements'] = extra_requirements

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
                                   password = password,
                                   sample_description = sample_description,
                                   extra_requirements = extra_requirements
                                   )
        else:
            hashed_password = generate_password_hash(password)
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

    #return render_template('returning_user_login.html', user = current_user)




@views.route("/returning_user_booking", methods=['GET', 'POST'])
@login_required
def returning_user_booking():
    selected_lab_id = session.get('selected_lab_id')
    with db.session() as db_session:
        lab_choice = db_session.query(labs).get_or_404(selected_lab_id)
        return render_template('returning_user_booking.html', 
                                user = current_user,
                                lab_choice = lab_choice)



@views.route('/confirmation_new_user', methods=['GET', 'POST'])
@login_required
def confirmation_new_user():
    selected_test = session.get('selected_test')
    first_name = session.get('first_name', None)
    sample_description = session.get('sample_description')
    extra_requirements = session.get('extra_requirements')

    selected_lab_name = session.get('selected_lab_name')
    with db.session() as db_session:
        selected_lab_id = db_session.query(labs.id) \
            .filter(labs.name == selected_lab_name) \
            .scalar()
        lab_choice = labs.query.get_or_404(selected_lab_id)
        lab_id = lab_choice.id

        current_user_id = current_user.id
        submitted_datetime = datetime.datetime.now()
        formatted_date = submitted_datetime.strftime("%Y-%m-%d %H:%M:%S")
        date_to_string = str(formatted_date)

        # Save the testing info to the requests table.
        new_request = test_requests(sample_description = sample_description,
                                    extra_requirements = extra_requirements,
                                    test_name = selected_test,
                                    lab_id = lab_id,
                                    approval_status = 'Pending',
                                    requestor_id = current_user_id,
                                    payment_status = 'Not Paid',
                                    transit_status = 'Not Shippied',
                                    datetime_submitted = date_to_string
                                    )

        db.session.add(new_request)
        db.session.commit()

        return render_template('confirmation.html', 
                                selected_test = selected_test,
                                first_name = first_name,
                                lab_choice = lab_choice,
                                user = current_user
                                )


@views.route('/confirmation_returning_user', methods=['GET', 'POST'])
@login_required
def confirmation_returning_user():
    if request.method == 'POST':
        sample_description = request.form['sample_description']
        extra_requirements = request.form['extra_requirements']

        selected_test = session.get('selected_test')
        selected_lab_id = session.get('selected_lab_id')
        
        with db.session() as db_session:
            lab_choice = db_session.query(labs).get_or_404(selected_lab_id)
            lab_id = lab_choice.id

            # May not need this code block. On the HTML page, you could probably just use 
            # {{ user.first_name }} to get the first name (assuming you pass 'user = current_user'
            # to the HTML template).
            current_user_id = current_user.id
            logged_in_user = db_session.query(individuals_login).filter_by(id = current_user_id).first()
            name = logged_in_user.first_name

            submitted_datetime = datetime.datetime.now()
            formatted_date = submitted_datetime.strftime("%Y-%m-%d %H:%M:%S")
            date_to_string = str(formatted_date)

            # Save the testing info to the test_requests db table.
            new_request = test_requests(sample_description = sample_description,
                                        extra_requirements = extra_requirements,
                                        test_name = selected_test,
                                        approval_status = 'Pending',
                                        lab_id = lab_id,
                                        requestor_id = current_user_id,
                                        payment_status = 'Not Paid',
                                        transit_status = 'Not Shippied',
                                        datetime_submitted = date_to_string
                                        )


            db.session.add(new_request)
            db.session.commit()

            return render_template('confirmation.html', 
                                selected_test = selected_test,
                                first_name = name,
                                lab_choice = lab_choice,
                                user = current_user
                                )




@views.route('/lab_requests', methods=['GET', 'POST'])
@login_required
def lab_requests():
    try:
        if request.method == 'POST':
            try:
                request_id = request.form['id']
                action = request.form['action']

                if action == 'approve':
                    status = 'Approved'
                elif action == 'deny':
                    status = 'Need more details'
                else:
                    status = None
        
                if status:
                    with db.session() as db_session:
                        db_session.query(test_requests).filter_by(request_id = request_id).update({'approval_status': status})
                        db.session.commit()
                    
                    flash('Status updated successfully', 'success')
                else:
                    flash('Invalid action.', 'error')

                return redirect(url_for('views.lab_requests'))

            # Handle any exceptions that might occur when processing the POST request. It 
            # catches any KeyError exceptions that might occur if the 'id' or 'action' 
            # keys are not present in the request form.
            except KeyError:
                flash('Invalid request.', 'error')
                return redirect(url_for('views.lab_requests'))

            except Exception as e:
                flash('An error occurred: ' + str(e), 'error')
                return redirect(url_for('views.lab_requests'))

        # Handle any exceptions that might occur when retrieving the lab information 
        # and test requests from the database. It catches any AttributeError exceptions 
        # that might occur if the user information is invalid, and catches any other 
        # exceptions that might occur.
        try:
            with db.session() as db_session:
                lab_info_id = db_session.query(labs_login).filter_by(id = current_user.id).first().lab_id # this is an integer type
                lab_requests = db_session.query(test_requests) \
                                        .filter_by(lab_id = lab_info_id) \
                                        .order_by(test_requests.datetime_submitted.desc()) \
                                        .all() # this is a list type

        except AttributeError:
            flash('Invalid user information.', 'error')
            return redirect(url_for('views.lab_requests'))

        # Catch any other exceptions that might occur while running the code, 
        # and displays an error message to the user.
        except Exception as e:
            flash('An error occurred: ' + str(e), 'error')
            return redirect(url_for('views.lab_requests'))

        return render_template('lab_requests.html', 
                                user = current_user,
                                lab_requests = lab_requests)

    except Exception as e:
        flash('An error occurred: ' + str(e), 'error')
        return redirect(url_for('views.lab_requests'))





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
        request_id = list(data[0].values())[0]
        new_details = list(data[2].values())[0]
        status = 'Need more details'

        with db.session() as db_session:
            db_session.query(test_requests) \
                .filter_by(request_id = request_id) \
                .update({'approval_status': status})
            db_session.commit()

        # SEND AN EMAIL TO THE CUSTOMER

        return data
    
    # THIS CAN PROBABLY BE REMOVED
    # Handle GET requests
    # else:
    #     lab_info_id = labs_login.query.filter_by(id = current_user.id).first().lab_id # this is an integer type
    #     lab_requests = test_requests.query.filter_by(lab_id = lab_info_id).all() # this is a list type

    #     request_dicts = []
    #     for each in lab_requests:
    #         request_dict = {
    #             'test_name': each.test_name,
    #             'sample_name': each.sample_name,
    #             'sample_description': each.sample_description,
    #             'turnaround': each.turnaround,
    #             'status': each.status
    #         }
    #         request_dicts.append(request_dict)

    #     json_data = jsonify(request_dicts)
    #     return json_data






@views.route('/upload', methods = ['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        request_id = request.form['id']
        file = request.files['file']
        if file:
            file_data = file.read()

            db.session.query(test_requests).filter_by(request_id = request_id).update({'results': file_data})
            db.session.commit()
            db.session.close()
            flash('File was successfully uploaded!', 'success')
            return redirect(url_for('views.lab_requests'))
        else:
            flash('There was an error handling your upload.', 'error')
            return redirect(url_for('views.lab_requests'))




@views.route('/download/<int:request_id>')
def download(request_id):
    result = db.session.query(test_requests).filter_by(request_id=request_id).first()

    if result:
        file_data = result.results

        response = Response(file_data, mimetype='application/octet-stream')
        response.headers.set('Content-Disposition', 'attachment', filename='results.pdf')
        return response
    
    else:
        flash("Error: Request not found or no results available.", "error")
        return redirect(url_for("views.lab_requests"))






@views.route("/user_requests", methods=['GET', 'POST'])
@login_required
def user_requests():
    if request.method == 'POST':
        # If the user wants to get a shipping label with their test.
        lab_name = request.form['lab_name']
        session['lab_name_for_shipping_label'] = lab_name
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

            current_user_lab_id = current_user.lab_id

            # Join 'labs_tests' and 'tests' tables on 'test_id' column
            joined_data = db_session.query(labs_tests, tests).join(tests, labs_tests.test_id == tests.id)

            # Filter the joined data by the given lab_id
            tests_for_lab = joined_data.filter(labs_tests.lab_id == current_user_lab_id)

            # Extract the test names from the joined data
            test_names = [test.name for _, test in tests_for_lab]

            if test_name in test_names:
                prev_page_url = url_for('views.provider_settings')
                flash(Markup(f'That test is already in your offerings. Please edit the \
                      test parameters on the <a href="{prev_page_url}">previous page</a>.'), 'error')
                
                test_names = db_session.query(tests.name).order_by(tests.name).all()
                # Convert list of tuples to list of strings:
                test_names = [name[0] for name in test_names]

                return render_template('add_new_test.html',
                                       user = current_user,
                                       test_names = test_names
                                       )

            new_lab_test = labs_tests(lab_id = current_user_lab_id, 
                                    test_id = new_test.id,
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
        distance_units = request.form['distance_units']
        weight = request.form['weight']
        weight_units = request.form['weight_units']

        parcel = {
            "length": length,
            "width": width,
            "height": height,
            "distance_unit": distance_units,
            "weight": weight,
            "mass_unit": weight_units
            }



        shipment = shippo.Shipment.create(
            address_from = address_from,
            address_to = address_to,
            parcels = [parcel],
            asynchronous = False
            )


        rates = shipment.rates
        sorted_rates = sorted(rates, key=lambda resp: float(resp['amount']))



        # transaction = shippo.Transaction.create(
        #     rate=selected_rate_object_id, asynchronous=False)
        

        # # print the shipping label from label_url
        # # Get the tracking number from tracking_number
        # ##### "transacation.label_url" is the url that will take the user
        # # to the shipping label.
        # if transaction.status == "SUCCESS":
        #     print("Purchased label with tracking number %s" %
        #         transaction.tracking_number)
        #     print("The label can be downloaded at %s" % transaction.label_url)
        # else:
        #     print("Failed purchasing the label due to:")
        #     for message in transaction.messages:
        #         print("- %s" % message['text'])
        
        return render_template('shipping_rates.html',
                               user = current_user,
                               rates = sorted_rates)

        #return render_template('label.html', label_url = label_url)



    lab_name = session.get('lab_name_for_shipping_label')
    lab = labs.query.filter_by(name = lab_name).first()

    return render_template('shipping.html', 
                           user = current_user,
                           lab = lab
                           )






@views.route('/checkout/<string:lab_name>/<string:test_name>', methods=['GET', 'POST'])
def checkout(lab_name, test_name):
    if request.method == 'POST':
        lab_object = labs.query.filter_by(name = lab_name).first()
        print(lab_object)
        lab_id = lab_object.id

        test_object = tests.query.filter_by(name = test_name).first()
        print(test_object)
        test_id = test_object.id

        row_in_labs_tests = labs_tests.query.filter_by(lab_id = lab_id,
                                           test_id = test_id).first()
        price = row_in_labs_tests.price
        stripe_price = round(price * 100)

        stripe.api_key = os.getenv('stripe_secret_key')

        session = stripe.checkout.Session.create(
            payment_method_types = ['card'],
            line_items = [{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': stripe_price,
                    'product_data': {
                        'name': test_name,
                    },
                },
                'quantity': 1,
            }],
            mode = 'payment',
            success_url = url_for('views.success', _external = True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url = url_for('views.index', _external = True)
        )
        return redirect(session.url)


@views.route('/order/success')
def success():
    session_id = request.args.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status == 'paid':
        # Payment was successful, show success page
        return render_template('order_success.html')
    else:
        # Payment was not successful, show error page
        return render_template('order_error.html')











@views.route("/privacy_policy", methods=['GET', 'POST'])
def privacy_policy():
    return render_template('privacy_policy.html', 
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