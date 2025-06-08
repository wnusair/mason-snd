from tutorial import create_app
from tutorial.extensions import db
from tutorial.models import *

app = create_app()

with app.app_context():
    db.create_all()
    print("✅ Database created successfully.")
