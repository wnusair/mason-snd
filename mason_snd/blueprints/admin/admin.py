from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.admin import User_Requirements, Requirements

from werkzeug.security import generate_password_hash, check_password_hash

admin_bp = Blueprint('admin', __name__, template_folder='templates')

user_id = session.get('user_id')
user = User.query.filter_by(id=user_id).first()
print(user)

def create_requirements():
    """
    
    
    """

@admin_bp.route('/')
def index():
    if user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index'))
    return render_template('admin/index.html')

@admin_bp.route('/add_popup', methods=['POST', 'GET'])
def add_popup():
    if user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index'))

    if request.method == 'POST':
        recipient_first_name = request.form.get('recipient_first_name')
        recipient_last_name = request.form.get('recipient_last_name')
        message = request.form.get('message')

        recipient = User.query.filter_by(first_name=recipient_first_name, last_name=recipient_last_name).first()

        if not recipient:
            flash("Recipient Does Not Exist, Please retype name")
            return redirect(url_for('admin.add_popup'))
        
        #yu need to make popups with experation dates and checking if done

    
    return render_template('admin/add_popup.html')