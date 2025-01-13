from app import db
from models import User  # Assuming your models are in a file named `models.py`

def change_user_role():
    # Prompt for the username
    username = input("Enter the username of the user whose role you want to change: ")

    # Find the user in the database
    user = User.query.filter_by(username=username).first()

    if not user:
        print(f"User with username '{username}' not found.")
        return

    # Prompt for the new role
    new_role = input(f"Enter the new role for {username} (current role: {user.role}): ").strip()

    if not new_role:
        print("Role cannot be empty. Operation canceled.")
        return

    # Update the user's role
    user.role = new_role
    db.session.commit()

    print(f"Role of user '{username}' has been updated to '{new_role}'.")

if __name__ == "__main__":
    change_user_role()