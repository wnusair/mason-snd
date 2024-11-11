from app import app, db
from auth import auth as auth_blueprint, create_data_chairman
from routes import main as main_blueprint
from models import User, Event, Tournament, Statistics

# Register blueprints
app.register_blueprint(auth_blueprint)
app.register_blueprint(main_blueprint)




if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database tables created.")
        
        # Print existing tables
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        print("Existing tables:", existing_tables)
        

    app.run(host="0.0.0.0", port=5000)
