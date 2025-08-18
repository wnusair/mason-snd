#!/usr/bin/env python3
"""
Check form field details
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.tournaments import Tournament, Form_Fields

app = create_app()

with app.app_context():
    tournament = Tournament.query.first()
    
    form_fields = Form_Fields.query.filter_by(tournament_id=tournament.id).all()
    print(f"Tournament: {tournament.name}")
    print(f"Form fields: {len(form_fields)}")
    
    for field in form_fields:
        print(f"\nField ID: {field.id}")
        print(f"Label: '{field.label}'")
        print(f"Type: {field.type}")
        print(f"Options: '{field.options}'")
        print(f"Required: {field.required}")
