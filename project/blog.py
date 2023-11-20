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


@blog.route("/elemental-analysis", methods=['GET', 'POST'])
def elemental_analysis():
    url = 'https://www.unifiedsl.com/blog/elemental-analysis'
    title = 'Decoding Matter: The Art and Science of Quantitative Elemental Analysis'
    description = "Quantitative elemental analysis empowers scientists and researchers to decipher the secrets held within matter, offering a precise and detailed view of the elemental composition of substances."

    return render_template('chemical/elemental.html',
                    user = current_user,
                    title = title,
                    description = description,
                    url = url
                    )

@blog.route("/mass-spectrometry", methods=['GET', 'POST'])
def mass_spectrometry():
    url = 'https://www.unifiedsl.com/blog/mass-spectrometry'
    title = 'Mastering Mass: The Wonders of Mass Spectrometry'
    description = "Mass spectrometry is a journey into the molecular realm, enabling scientists to unravel the mysteries of matter at the atomic and molecular levels. From deciphering the complexities of biological systems to identifying environmental pollutants, the wonders of mass spectrometry continue to shape the landscape of scientific discovery."

    return render_template('chemical/mass_spec.html',
                    user = current_user,
                    title = title,
                    description = description,
                    url = url
                    )


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
                    url = url
                    )