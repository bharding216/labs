from flask import Flask, session, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_session import Session
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
import os
from helpers import my_enumerate, generate_sitemap
from dotenv import load_dotenv
import logging

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)

    app.config['STRIPE_PUBLIC_KEY'] = os.getenv('stripe_public_key')
    app.config['STRIPE_SECRET_KEY'] = os.getenv('stripe_secret_key')
    app.config['RECAPTCHA_SITE_KEY']= os.getenv('recaptcha_site_key')
    app.config['RECAPTCHA_SECRET_KEY'] = os.getenv('recaptcha_secret_key')

    load_dotenv()
    # Create my_enumerate function and make it available globally.
    app.jinja_env.globals.update(my_enumerate = my_enumerate)
    app.jinja_env.globals.update(generate_sitemap = generate_sitemap)

    app.config['MYSQL_HOST'] = os.getenv('mysql_host')
    app.config['MYSQL_USER'] = os.getenv('mysql_user')
    app.config['MYSQL_PASSWORD'] = os.getenv('mysql_password')
    app.config['MYSQL_DB'] = os.getenv('mysql_db')
    app.config['SECRET_KEY'] = os.getenv('secret_key')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_COOKIE_SECURE'] = True
    Session(app)

    # Mail config settings:
    app.config['MAIL_SERVER']='live.smtp.mailtrap.io'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USERNAME'] = 'api'
    app.config['MAIL_PASSWORD'] = os.getenv('mail_password')
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://' + os.getenv('mysql_user') + \
        ':' + os.getenv('mysql_password') + '@' + os.getenv('mysql_host') + '/' + os.getenv('mysql_db')
    
    # SQLALCHEMY_POOL_SIZE: This setting determines the maximum 
    # number of connections that can be created in the pool. 
    # A good rule of thumb is to set this value to the maximum 
    # number of concurrent requests your application is expected 
    # to handle, plus a few extra connections for overhead.
    # The ClearDB (MySQL) max connections for the free plan is 10.
    app.config['SQLALCHEMY_POOL_SIZE'] = 5

    # SQLALCHEMY_POOL_RECYCLE: This setting determines how long a 
    # connection can remain in the pool before it is recycled and 
    # replaced with a new connection. A good starting value for this 
    # setting is around 5-10 minutes (300-600 seconds). However, you 
    # should adjust this value based on the expected duration of your 
    # requests and the resources available on your database server. If 
    # your requests are short-lived, you may be able to increase this 
    # value to reduce the overhead of creating and closing connections.
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 450

    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 2

    # SQLALCHEMY_POOL_TIMEOUT: This setting determines how long 
    # a connection can remain idle before it is closed and removed 
    # from the pool. A good starting value for this setting is 
    # around 30 seconds. However, you should adjust this value based 
    # on the expected duration of your requests and the resources 
    # available on your database server. If your requests are short-lived, 
    # you may be able to increase this value to reduce the overhead 
    # of creating and closing connections.
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,  # enable connection pool pre-ping
    }

    db.init_app(app)
    mail.init_app(app)

    with app.app_context():
        from .views import views
        from .blog import blog
        from .contact import contact_bp
        from .auth import auth_bp
        from .models import labs_login, individuals_login

        app.register_blueprint(views, url_prefix="/")
        app.register_blueprint(blog, url_prefix="/blog")
        app.register_blueprint(contact_bp, url_prefix="/contact")
        app.register_blueprint(auth_bp, url_prefix="/auth")

        db.create_all()

        login_manager.login_view = "views.returning_user_login"
        login_manager.login_message = ""
        login_manager.login_message_category = "error"
        login_manager.init_app(app)

        # When a user logs in, their `id` is stored in a 
        # session cookie. When a request is made to the application,
        # Flask-Login calls the `load_user` function to load the user
        # object associated with that `id`.  

        # Once the user object is loaded, Flask-Login stores it in
        # the `current_user` object, which can be accessed in your 
        # views.
        @login_manager.user_loader
        def load_user(id):
            type = session.get('type')
            if type == 'lab':
                user = labs_login.query.filter_by(id = id).first()
            elif type == 'customer':
                user = individuals_login.query.filter_by(id = id).first()
            else:
                user = None
            return user


        @app.before_request
        def redirect_to_https():
            # Ensure that all requests are secure (HTTPS)
            if not request.is_secure and request.host != 'localhost:2000':
                return redirect(request.url.replace('http://', 'https://'), code=301)

        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

        return app