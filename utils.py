import csv
from io import TextIOWrapper, StringIO
from models import User, Event, Tournament, Statistics
from flask import send_file
import random
from datetime import datetime, timedelta
from app import db

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_csv(file):
    csv_file = TextIOWrapper(file, encoding='utf-8')
    csv_reader = csv.DictReader(csv_file)
    statistics = []

    for row in csv_reader:
        user = User.query.filter_by(username=row['username']).first()
        if not user:
            user = User(username=row['username'], email=f"{row['username']}@example.com", role='Participant', is_participant=True)
            db.session.add(user)
        
        event = Event.query.filter_by(name=row['event']).first()
        tournament = Tournament.query.filter_by(name=row['tournament']).first()

        if not event or not tournament:
            raise ValueError(f"Invalid data in row: {row}")

        statistic = Statistics(
            user_id=user.id,
            event_id=event.id,
            tournament_id=tournament.id,
            score=float(row['score']),
            notes=row['notes'],
            date=datetime.strptime(row['date'], '%Y-%m-%d')
        )
        statistics.append(statistic)

    db.session.commit()
    return statistics

def generate_sample_csv():
    users = User.query.all()
    events = Event.query.all()
    tournaments = Tournament.query.all()

    if not users or not events or not tournaments:
        return "Error: Not enough data to generate sample CSV"

    csv_data = StringIO()
    csv_writer = csv.writer(csv_data)

    # Write header
    csv_writer.writerow(['username', 'event', 'tournament', 'score', 'notes', 'date'])

    # Generate 50 sample rows
    for _ in range(50):
        user = random.choice(users)
        event = random.choice(events)
        tournament = random.choice(tournaments)
        score = round(random.uniform(0, 100), 2)
        notes = f"Sample note for {user.username} in {event.name}"
        date = (datetime.now() - timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d')

        csv_writer.writerow([user.username, event.name, tournament.name, score, notes, date])

    # Prepare the CSV file for download
    csv_data.seek(0)
    return send_file(csv_data,
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='sample_tournament_stats.csv')
