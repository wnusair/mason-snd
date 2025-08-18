from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.tournaments import Tournament_Signups, Tournament_Judges
from mason_snd.models.events import Event
from mason_snd.models.auth import User

app = create_app()

with app.app_context():
    print("=== TESTING VIEW_TOURNAMENT LOGIC ===")
    tournament_id = 1
    
    # Test get_signups_by_event function
    signups = Tournament_Signups.query.filter_by(tournament_id=tournament_id, is_going=True).all()
    print(f"\nSignups for tournament {tournament_id} (is_going=True): {len(signups)}")
    
    event_dict = {}
    for signup in signups:
        if signup.event_id not in event_dict:
            event_dict[signup.event_id] = []
        event_dict[signup.event_id].append(signup)
    
    print(f"Events with signups: {list(event_dict.keys())}")
    for event_id, signups_list in event_dict.items():
        event = Event.query.filter_by(id=event_id).first()
        print(f"  Event {event_id} ({event.event_name if event else 'Unknown'}): {len(signups_list)} signups")
    
    # Test judges
    judges = Tournament_Judges.query.filter_by(tournament_id=tournament_id, accepted=True).all()
    print(f"\nAccepted judges for tournament {tournament_id}: {len(judges)}")
    
    # Calculate roster counts
    speech_competitors = 0
    LD_competitors = 0
    PF_competitors = 0

    for judge in judges:
        event_id = judge.event_id
        event = Event.query.filter_by(id=event_id).first()
        
        if event:
            if event.event_type == 0:
                speech_competitors += 6
            elif event.event_type == 1:
                LD_competitors += 2
            else:
                PF_competitors += 4
    
    print(f"\nRoster capacity based on accepted judges:")
    print(f"  Speech competitors: {speech_competitors}")
    print(f"  LD competitors: {LD_competitors}")
    print(f"  PF competitors: {PF_competitors}")
    
    print(f"\nActual signups vs capacity:")
    for event_id, signups_list in event_dict.items():
        event = Event.query.filter_by(id=event_id).first()
        if event:
            if event.event_type == 0:
                capacity = speech_competitors
            elif event.event_type == 1:
                capacity = LD_competitors
            else:
                capacity = PF_competitors
            print(f"  {event.event_name}: {len(signups_list)} signups / {capacity} capacity")
