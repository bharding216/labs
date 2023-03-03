from flask import Blueprint, render_template, request, redirect, flash, url_for, session, send_file, jsonify
from flask_login import login_required, current_user, login_user
from .models import tests, labs, labs_tests, individuals_login, labs_login, test_requests
import datetime
from flask_mail import Message
from . import db, mail
from itsdangerous.url_safe import URLSafeSerializer
#from itsdangerous.serializer import Serializer
import yaml
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous.exc import BadSignature
import shippo
from io import BytesIO
import phonenumbers
from urllib.parse import quote, unquote
import os


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
            session['zipcode'] = zipcode
            date = request.form['date-picker']

            return redirect(url_for('views.lab_function'))


    else:
        with db.session() as db_session:
            test_names = db_session.query(tests).all()

            date_choice = datetime.datetime.now().strftime("%Y-%m-%d")

        return render_template('index.html', 
                               tests = test_names, 
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
        
        with db.session() as db_session:
            row_in_tests_table = db_session.query(tests) \
                .filter(tests.name == selected_test) \
                .first()
            id_in_tests_table = row_in_tests_table.id
            rows_in_labs_tests_table = db_session.query(labs_tests) \
                .filter(labs_tests.test_id == id_in_tests_table) \
                .all()

            # Change this to only query labs that can perform that test
            lab_query = db_session.query(labs).all()

        return render_template('labs.html', 
            lab_query = lab_query, 
            selected_test = selected_test, 
            price_table = rows_in_labs_tests_table,
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
        turnaround = request.form['turnaround']
        sample_description = request.form['sample_description']
        sample_name = request.form['sample_name']

        session['first_name'] = first_name
        session['sample_name'] = sample_name
        session['sample_description'] = sample_description
        session['turnaround'] = turnaround

        # Check if the phone number string has 10 characters. If it does,
        # add +1 to make it in the correct format for `phonenumbers`.
        # Then try to parse the phone number. If you can't parse it, then 
        # just save the user input and move on. 
        if len(phone) == 10:
            phone = "+1" + phone
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
                company_name = company_name,
                type = 'customer'
                )
            
            db.session.add(new_user)
            db.session.commit()

            with db.session() as db_session:
                user = db_session.query(individuals_login).filter_by(email = email).first()
                login_user(user, remember = True)
                session.permanent = True
                session['type'] = 'requestor'

            flash('New account successfully created.', category = 'success')
            return redirect(url_for('views.confirmation_new_user'))

    else:
        selected_lab_id = session.get('selected_lab_id')
        with db.session() as db_session:
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
    turnaround = session.get('turnaround')
    sample_name = session.get('sample_name')
    sample_description = session.get('sample_description')

    selected_lab_id = session.get('selected_lab_id')
    lab_choice = labs.query.get_or_404(selected_lab_id)
    lab_id = lab_choice.id
    current_user_id = current_user.id

    # save the testing info to the requests table.
    new_request = test_requests(sample_name = sample_name,
                           sample_description = sample_description,
                           turnaround = turnaround,
                           test_name = selected_test,
                           lab_id = lab_id,
                           status = 'Pending',
                           requestor_id = current_user_id
                           )

    db.session.add(new_request)
    db.session.commit()

    return render_template('confirmation.html', 
                           selected_test = selected_test,
                           first_name = first_name,
                           lab_choice = lab_choice,
                           turnaround = turnaround,
                           user = current_user
                           )


@views.route('/confirmation_returning_user', methods=['GET', 'POST'])
@login_required
def confirmation_returning_user():
    if request.method == 'POST':
        sample_name = request.form['sample_name']
        sample_description = request.form['sample_description']
        turnaround = request.form['turnaround']

        selected_test = session.get('selected_test')
        first_name = session.get('first_name', None)

        selected_lab_id = session.get('selected_lab_id')
        
        with db.session() as db_session:
            lab_choice = db_session.query(labs).get_or_404(selected_lab_id)
            lab_id = lab_choice.id

            # Save the testing info to the requests table.
            new_request = test_requests(sample_name = sample_name,
                                        sample_description = sample_description,
                                        turnaround = turnaround,
                                        test_name = selected_test,
                                        lab_id = lab_id,
                                        status = 'Pending'
                                        )

            db.session.add(new_request)
            db.session.commit()

        return render_template('confirmation.html', 
                            selected_test = selected_test,
                            first_name = first_name,
                            lab_choice = lab_choice,
                            turnaround = turnaround,
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
                    db.session.query(test_requests).filter_by(request_id = request_id).update({'status': status})
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
            lab_info_id = labs_login.query.filter_by(id = current_user.id).first().lab_id # this is an integer type
            lab_requests = test_requests.query.filter_by(lab_id = lab_info_id).all() # this is a list type

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

        db.session.query(test_requests).filter_by(request_id = request_id).update({'status': status})
        db.session.commit()

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
            flash('File was successfully uploaded!', 'success')
            return redirect(url_for('views.lab_requests'))
        else:
            flash('There was an error handling your upload.', 'error')
            return redirect(url_for('views.lab_requests'))


@views.route('/download/<int:request_id>')
def download(request_id):
    result = db.session.query(test_requests).filter_by(request_id=request_id).first()
    file_data = BytesIO(result.results)    
    
    if result:
        return send_file(file_data, 
                         mimetype='application/pdf', 
                         as_attachment=True, 
                         download_name='results.pdf')
    else:
        flash("Error: Request not found or no results available.", "error")
        return redirect(url_for("views.lab_requests"))



@views.route("/user_requests", methods=['GET', 'POST'])
@login_required
def user_requests():
    if request.method == 'POST':
        flash('The buttons work!', 'success')
        return redirect(url_for('views.user_requests'))

    my_requests = db.session.query(test_requests, labs.name) \
        .join(labs, test_requests.lab_id == labs.id) \
        .filter(test_requests.requestor_id == current_user.id) \
        .all()
    
    return render_template('user_requests.html', 
                            user = current_user,
                            my_requests = my_requests
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

        # Create a list of tuples, where each typle is a test name and price pair 
        # where the logged in user id is equal to the lab_id in the labs_tests table. 
        # tests_and_pricing = db.session.query(tests.name, labs_tests.price).\
        #                         join(labs_tests, tests.id == labs_tests.test_id).\
        #                         filter(labs_tests.lab_id == current_user_lab_id).\
        #                         order_by(tests.name.asc()).\
        #                         all()

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

                db.session.add(lab_login_object)
                db.session.commit()

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
    
    db.session.commit()
    flash('Your settings have been successfully updated!', 'success')

    return redirect(url_for('views.provider_settings'))



@views.route('/shipping', methods=['GET', 'POST'])
def shipping():
    if request.method == 'POST':
        with open('project/db.yaml', 'r') as file:
            test = yaml.load(file, Loader=yaml.FullLoader)

        # Shippo API Key:
        shippo.config.api_key = os.getenv('shippo_api_key')

        address_from = {
            "name": "John Doe",
            "street1": "6512 Green St",
            "city": "Philadelphia",
            "state": "PA",
            "zip": "19144",
            "country": "US",
            "phone": "555-555-5555",
            "email": "jdoe@example.com"
        }



        # from session get the selected lab
        # get company name, street, city, state, country, zip, phone, email

        address_to = {
            "name": "Jane Doe",
            "street1": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94105",
            "country": "US",
            "phone": "555-555-5555",
            "email": "jane.doe@example.com"
        }

        parcel = {
            "length": "5",
            "width": "5",
            "height": "5",
            "distance_unit": "in",
            "weight": "2",
            "mass_unit": "lb"
        }


        shipment = shippo.Shipment.create(
            address_from=address_from,
            address_to=address_to,
            parcels=[parcel],
            asynchronous=False
        )

        rates = shipment.rates



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
                               rates = rates)

        #return render_template('label.html', label_url = label_url)

    return render_template('shipping.html', user = current_user)



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
