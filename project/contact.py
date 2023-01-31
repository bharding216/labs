from flask import Blueprint, render_template, request, redirect, url_for
from .models import tests, labs
import datetime

contact_bp = Blueprint('contact', __name__, 
    template_folder='contact_templates', static_folder='contact_static')

@contact_bp.route('/', methods=['GET', 'POST'])
def contact_function():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']

        return redirect(url_for('contact.success', name=name,
            email=email, phone=phone, message=message))

    return render_template('contact.html')

@contact_bp.route('/success', methods=['GET'])
def success():
    name = request.args.get("name")
    return render_template('contact_success.html', name=name)