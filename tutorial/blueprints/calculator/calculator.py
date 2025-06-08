from flask import Blueprint, render_template, request, redirect, url_for

from tutorial.extensions import db
from tutorial.models.user import User, Order, Product
from tutorial.models.video import Video

calculator_bp = Blueprint('calculator', __name__, template_folder='templates')

@calculator_bp.route('/')
def index():
    return "Bloody damn"

@calculator_bp.route('/add/<int:a>/<int:b>')
def add(a, b):
    User.query
    return str(a + b)

@calculator_bp.route('/go_to_hello')
def go_to_hello():
    return redirect(url_for('helloworld.hello_html'))