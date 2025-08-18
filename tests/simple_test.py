print("Starting test...")

try:
    import sys
    import os
    sys.path.insert(0, os.path.abspath('.'))
    print("Path added successfully")
    
    from mason_snd import create_app
    print("App imported successfully")
    
    app = create_app()
    print("App created successfully")
    
    with app.app_context():
        from mason_snd.extensions import db
        from mason_snd.models.tournaments import Tournament
        print("Models imported successfully")
        
        tournaments = Tournament.query.all()
        print(f"Found {len(tournaments)} tournaments in database")
        
        for tournament in tournaments:
            print(f"Tournament: {tournament.name}, Results submitted: {tournament.results_submitted}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("Test completed.")
