from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import yaml
from flask_login import LoginManager


db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    with open('project/db.yaml', 'r') as file:
        test = yaml.load(file, Loader=yaml.FullLoader)
    app.config['MYSQL_HOST'] = test['mysql_host']
    app.config['MYSQL_USER'] = test['mysql_user']
    app.config['MYSQL_PASSWORD'] = test['mysql_password']
    app.config['MYSQL_DB'] = test['mysql_db']
    app.config['SECRET_KEY'] = test['secret_key']


    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://' + test['mysql_user'] + \
        ':' + test['mysql_password'] + '@' + test['mysql_host'] + '/' + test['mysql_db']
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    db.init_app(app)

    with app.app_context():

        from .views import views
        from .contact import contact_bp
        from .auth import auth_bp
        from .models import labs_login

        app.register_blueprint(views, url_prefix="/")
        app.register_blueprint(contact_bp, url_prefix="/contact")
        app.register_blueprint(auth_bp, url_prefix="/auth")


        db.create_all()

        login_manager.login_view = "auth_bp.lab_login"
        login_manager.login_message = ""
        login_manager.login_message_category = "error"
        login_manager.init_app(app)

        @login_manager.user_loader
        def load_user(id):
            return labs_login.query.get(int(id))



        return app