from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .models import individuals_login, labs_login
import datetime
from . import db
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

blog = Blueprint('blog', __name__, template_folder='blog_templates', static_folder='static')


@blog.route("/", methods=['GET', 'POST'])
def blog_home():
    return render_template('home.html',
                    user = current_user)


@blog.route("/particle-size-distribution", methods=['GET', 'POST'])
def psd():
    url = 'https://www.unifiedsl.com/blog/particle-size-distribution'
    title = 'Particle Size Distribution in Materials Analysis | Unified Labs'
    description = "In this comprehensive guide, we'll explore the different \
        techniques and technologies used for particle size distribution analysis, \
            and delve into the nuances and complexities of this fascinating field."

    return render_template('particle_size/psd.html',
                    user = current_user,
                    title = title,
                    description = description,
                    url = url)