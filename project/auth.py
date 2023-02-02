from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .models import tests, labs, labs_tests
import datetime

# Not done yet
# Create a separate auth folder for your auth-related
# templates and static files.