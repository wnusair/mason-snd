from werkzeug.security import check_password_hash
from app import db
from models import User

def get_user_info(user_id):
    user = User.query.get(int(user_id))
    if not user:
        return "User not found."

    print(f"Username: {user.username}")
    print(f"Email: {user.email}")

    # Prompt for password to check if it matches
    entered_password = input("Enter the password to verify: ")

    if check_password_hash(user.password_hash, entered_password):
        print("Password verified successfully.")
    else:
        print("Password verification failed.")

user_id = input("Enter user ID: ")
with db.app_context():
    get_user_info(user_id)