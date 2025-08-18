from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.tournaments import Tournament
from mason_snd.models.rosters import Roster
from mason_snd.models.auth import User
from mason_snd.blueprints.metrics.metrics import get_point_weights

app = create_app()

with app.app_context():
    print("=== TESTING WEIGHTED POINTS IN ROSTERS ===")
    
    # Get point weights
    tournament_weight, effort_weight = get_point_weights()
    print(f"Point weights: Tournament={tournament_weight}, Effort={effort_weight}")
    
    # Check if there are any tournaments
    tournaments = Tournament.query.all()
    print(f"Found {len(tournaments)} tournaments")
    for tournament in tournaments[:3]:
        print(f"  Tournament {tournament.id}: {tournament.name}")
    
    # Check if there are any saved rosters
    rosters = Roster.query.all()
    print(f"Found {len(rosters)} saved rosters")
    for roster in rosters[:3]:
        print(f"  Roster {roster.id}: {roster.name}")
    
    # Test the template calculation logic for a few users
    users = User.query.limit(3).all()
    print(f"\nTesting template calculation for {len(users)} users:")
    for user in users:
        tournament_points = user.tournament_points or 0
        effort_points = user.effort_points or 0
        
        # This is the exact calculation used in the templates
        weighted_points = ((tournament_points * tournament_weight) + (effort_points * effort_weight))
        rounded_weighted_points = round(weighted_points, 2)
        
        print(f"  {user.first_name} {user.last_name}:")
        print(f"    Tournament: {tournament_points}, Effort: {effort_points}")
        print(f"    Weighted: {weighted_points:.4f} -> {rounded_weighted_points}")
    
    print("\n=== Template Formula Test ===")
    # Test the exact Jinja2 template formula
    if users:
        user = users[0]
        template_formula = f"((({user.tournament_points or 0}) * {tournament_weight} + ({user.effort_points or 0}) * {effort_weight}) | round(2))"
        actual_result = round(((user.tournament_points or 0) * tournament_weight + (user.effort_points or 0) * effort_weight), 2)
        print(f"Template formula: {template_formula}")
        print(f"Actual result: {actual_result}")
