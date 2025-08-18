from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    admin = User.query.filter_by(email='admin@test.com').first()
    if not admin:
        admin = User(
            first_name='Admin',
            last_name='User',
            email='admin@test.com',
            password=generate_password_hash('admin123'),
            role=2,
            is_parent=False,
            account_claimed=True
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created: admin@test.com / admin123')
    else:
        print('Admin user already exists')
