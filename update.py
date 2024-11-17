# update_statistics.py
from app import app, db  # Import your app object
from models import Statistics, User

def populate_added_by_user_id():
    # Set a default user (you can choose an appropriate one)
    default_user = User.query.first()  # Replace with a specific user if needed
    if default_user:
        for stat in Statistics.query.all():
            if stat.added_by_user_id is None:
                stat.added_by_user_id = default_user.id
        db.session.commit()
        print("Updated all statistics with a default added_by_user_id.")

# Use the application context
with app.app_context():
    populate_added_by_user_id()
