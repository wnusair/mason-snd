"""
Create sample data to demonstrate the user metrics functionality
"""
import sys
import os
sys.path.append('/workspaces/mason-snd')

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.tournaments import Tournament, Tournament_Performance
from mason_snd.models.events import Event, User_Event, Effort_Score
from datetime import datetime, timedelta
import pytz
import random

EST = pytz.timezone('US/Eastern')

def create_sample_data():
    """Create sample data for demonstration"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if we already have tournament data
            if Tournament_Performance.query.count() > 0:
                print("Sample data already exists!")
                return
            
            # Get first few users
            users = User.query.limit(5).all()
            if not users:
                print("No users found to create sample data")
                return
            
            # Create sample tournaments
            tournaments = []
            for i in range(3):
                tournament = Tournament(
                    name=f"Sample Tournament {i+1}",
                    date=datetime.now(EST) - timedelta(days=30*i),
                    address=f"Sample Location {i+1}",
                    signup_deadline=datetime.now(EST) - timedelta(days=30*i + 7),
                    performance_deadline=datetime.now(EST) - timedelta(days=30*i - 1),
                    results_submitted=True
                )
                db.session.add(tournament)
                tournaments.append(tournament)
            
            db.session.commit()
            print(f"✓ Created {len(tournaments)} sample tournaments")
            
            # Create sample performances
            for user in users:
                for tournament in tournaments:
                    points = random.randint(10, 100)
                    bid = points > 70
                    rank = random.randint(1, 50)
                    stage = random.randint(0, 3) if points > 50 else 0
                    
                    performance = Tournament_Performance(
                        points=points,
                        bid=bid,
                        rank=rank,
                        stage=stage,
                        user_id=user.id,
                        tournament_id=tournament.id
                    )
                    db.session.add(performance)
            
            db.session.commit()
            print(f"✓ Created sample tournament performances for {len(users)} users")
            
            # Create sample events and effort scores
            events = Event.query.limit(3).all()
            if events:
                for user in users:
                    for event in events:
                        # Create user-event relationship
                        user_event = User_Event.query.filter_by(user_id=user.id, event_id=event.id).first()
                        if not user_event:
                            user_event = User_Event(
                                user_id=user.id,
                                event_id=event.id,
                                active=True
                            )
                            db.session.add(user_event)
                        
                        # Create effort scores
                        for i in range(3):
                            effort_score = Effort_Score(
                                score=random.randint(1, 10),
                                timestamp=datetime.now(EST) - timedelta(days=random.randint(1, 60)),
                                user_id=user.id,
                                event_id=event.id
                            )
                            db.session.add(effort_score)
                
                db.session.commit()
                print(f"✓ Created sample effort scores for {len(users)} users and {len(events)} events")
            
            print("\n✅ Sample data created successfully!")
            print("You can now test the user metrics functionality with realistic data.")
            
        except Exception as e:
            print(f"❌ Error creating sample data: {e}")
            db.session.rollback()

if __name__ == '__main__':
    create_sample_data()