from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.tournaments import Tournament, Tournament_Signups, Tournament_Judges
from mason_snd.models.auth import User

app = create_app()

with app.app_context():
    tournaments = Tournament.query.all()
    print(f"Tournaments: {len(tournaments)}")
    for t in tournaments:
        print(f"  - {t.name} (ID: {t.id})")
    
    signups = Tournament_Signups.query.all()
    print(f"\nTournament Signups: {len(signups)}")
    for s in signups:
        user = User.query.get(s.user_id)
        print(f"  - {user.first_name if user else 'Unknown'} -> Tournament {s.tournament_id}, Event {s.event_id}, Going: {s.is_going}")
    
    judges = Tournament_Judges.query.all()
    print(f"\nTournament Judges: {len(judges)}")
    for j in judges:
        child = User.query.get(j.child_id)
        judge = User.query.get(j.judge_id) if j.judge_id else None
        print(f"  - Child: {child.first_name if child else 'Unknown'}, Judge: {judge.first_name if judge else 'None'}, Accepted: {j.accepted}")
