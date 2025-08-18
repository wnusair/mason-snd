#!/usr/bin/env python3
"""
Script to add the Roster_Penalty_Entries table to the database
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import Roster_Penalty_Entries

def add_penalty_table():
    """Add the penalty entries table to the database"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create the new table
            db.create_all()
            print("Successfully created Roster_Penalty_Entries table!")
            
        except Exception as e:
            print(f"Error creating table: {e}")

if __name__ == "__main__":
    add_penalty_table()
