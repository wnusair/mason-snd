from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges

from werkzeug.security import generate_password_hash, check_password_hash

admin_bp = Blueprint('admin', __name__, template_folder='templates')

@admin_bp.route('/')
def index():
    return render_template('admin/index.html')