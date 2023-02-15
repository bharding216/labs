from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
import yaml
from flask_login import LoginManager
from flask_session import Session
from flask_mail import Mail
from datetime import timedelta
from itsdangerous import URLSafeTimedSerializer
import shippo


db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)

    with open('project/db.yaml', 'r') as file:
        test = yaml.load(file, Loader=yaml.FullLoader)
    app.config['MYSQL_HOST'] = test['mysql_host']
    app.config['MYSQL_USER'] = test['mysql_user']
    app.config['MYSQL_PASSWORD'] = test['mysql_password']
    app.config['MYSQL_DB'] = test['mysql_db']
    app.config['SECRET_KEY'] = test['secret_key']
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_COOKIE_SECURE'] = True
    Session(app)


    # Mail config settings:
    app.config['MAIL_SERVER']='sandbox.smtp.mailtrap.io'
    app.config['MAIL_PORT'] = 2525
    app.config['MAIL_USERNAME'] = 'c14de80d53a0d6'
    app.config['MAIL_PASSWORD'] = test['mail_password']
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False


    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://' + test['mysql_user'] + \
        ':' + test['mysql_password'] + '@' + test['mysql_host'] + '/' + test['mysql_db']
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    db.init_app(app)
    mail.init_app(app)
    
    with app.app_context():

        from .views import views
        from .contact import contact_bp
        from .auth import auth_bp
        from .models import labs_login, individuals_login

        app.register_blueprint(views, url_prefix="/")
        app.register_blueprint(contact_bp, url_prefix="/contact")
        app.register_blueprint(auth_bp, url_prefix="/auth")


        db.create_all()

        login_manager.login_view = "auth_bp.lab_login"
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
            elif type == 'requestor':
                user = individuals_login.query.filter_by(id = id).first()
            else:
                user = None
            return user


        return app