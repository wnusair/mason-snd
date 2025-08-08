import csv
from io import StringIO
from math import ceil

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response

from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.admin import User_Requirements, Requirements
from mason_snd.models.tournaments import Tournament, Tournament_Performance
from mason_snd.models.events import Event, User_Event, Effort_Score
from mason_snd.models.metrics import MetricsSettings
from sqlalchemy import asc, desc, func

rosters_bp = Blueprint('rosters', __name__, template_folder='templates')

"""

index:
- list tournaments let click

view_roster:
- once you open the tournmanet you can see the three roster views
    - judge view which shows a judge and then all the people that judge is bringing and their info displayed in the manage member view in events
    - event view which shows a table for every event and the ranking for each people (info like above) coming for that event and on the far right a table of the judges their child and how many people they can bring
    - rank view which just shows one table with members (info like above) their event and a judge table on the far right with the info like shown above

- for a judge in LD

"""
