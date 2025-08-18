from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.metrics import MetricsSettings
from mason_snd.blueprints.metrics.metrics import get_point_weights

app = create_app()

with app.app_context():
    print("=== TESTING WEIGHTED POINTS CALCULATION ===")
    
    # Get current point weights
    tournament_weight, effort_weight = get_point_weights()
    print(f"Current weights: Tournament={tournament_weight}, Effort={effort_weight}")
    
    # Get a few users to test with
    users = User.query.limit(5).all()
    print(f"\nTesting weighted points calculation for {len(users)} users:")
    
    for user in users:
        tournament_points = user.tournament_points or 0
        effort_points = user.effort_points or 0
        total_points = tournament_points + effort_points
        weighted_points = tournament_points * tournament_weight + effort_points * effort_weight
        
        print(f"  {user.first_name} {user.last_name}:")
        print(f"    Tournament Points: {tournament_points}")
        print(f"    Effort Points: {effort_points}")
        print(f"    Total Points: {total_points}")
        print(f"    Weighted Points: {weighted_points:.2f}")
        print()
    
    # Test that the template calculation would match
    sample_user = users[0] if users else None
    if sample_user:
        template_calc = (sample_user.tournament_points or 0) * tournament_weight + (sample_user.effort_points or 0) * effort_weight
        print(f"Template calculation verification for {sample_user.first_name}: {template_calc:.2f}")
