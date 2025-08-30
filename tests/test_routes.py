from mason_snd import create_app
from flask import url_for

app = create_app()

with app.app_context():
    print("Testing route URLs:")
    print("delete_management:", url_for('admin.delete_management'))
    print("delete_users:", url_for('admin.delete_users'))
    print("delete_tournaments:", url_for('admin.delete_tournaments'))
    print("All routes working correctly!")
