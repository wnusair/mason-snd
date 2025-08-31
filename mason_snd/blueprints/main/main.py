from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, send_from_directory, current_app
import csv
from io import StringIO
import os
from datetime import datetime, timezone

from mason_snd.extensions import db
from mason_snd.models.events import Event, User_Event, Effort_Score
from mason_snd.models.auth import User
from mason_snd.models.metrics import MetricsSettings

from werkzeug.security import generate_password_hash, check_password_hash

main_bp = Blueprint('main', __name__, template_folder='templates')

@main_bp.route('/')
def index():
    user_id = session.get('user_id')

    if user_id is not None:
        return redirect(url_for('profile.index', user_id=user_id))

    return render_template('main/index.html', user_id=user_id)

@main_bp.route('/life')
def life():
    return render_template('main/life.html')

@main_bp.route('/favicon.ico')
@main_bp.route('/favicon')
def favicon():
    """Serve the favicon from the static directory."""
    # Get the path to the mason_snd directory (three levels up from main.py)
    current_file_dir = os.path.dirname(__file__)  # main directory
    blueprints_dir = os.path.dirname(current_file_dir)  # blueprints directory
    mason_snd_dir = os.path.dirname(blueprints_dir)  # mason_snd directory
    static_dir = os.path.join(mason_snd_dir, 'static')
    
    # Check if the file exists
    icon_path = os.path.join(static_dir, 'icon.png')
    if not os.path.exists(icon_path):
        current_app.logger.error(f"Favicon not found at: {icon_path}")
        return "Favicon not found", 404
    
    response = send_from_directory(static_dir, 'icon.png', mimetype='image/png')
    # Add cache headers to ensure the favicon is cached properly
    response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 1 day
    response.headers['Expires'] = 'Wed, 31 Dec 2025 23:59:59 GMT'
    return response

@main_bp.route('/sitemap.xml')
def sitemap():
    """Generate an XML sitemap for the website."""
    
    # Get the base URL from the request
    base_url = request.url_root.rstrip('/')
    
    # Define all the static routes in the application
    static_routes = [
        {'url': '/', 'priority': '1.0', 'changefreq': 'daily'},
        {'url': '/life', 'priority': '0.5', 'changefreq': 'monthly'},
        {'url': '/auth/login', 'priority': '0.8', 'changefreq': 'monthly'},
        {'url': '/auth/register', 'priority': '0.8', 'changefreq': 'monthly'},
        {'url': '/auth/logout', 'priority': '0.3', 'changefreq': 'monthly'},
        {'url': '/events/', 'priority': '0.9', 'changefreq': 'weekly'},
        {'url': '/tournaments/', 'priority': '0.9', 'changefreq': 'weekly'},
        {'url': '/tournaments/add_tournament', 'priority': '0.7', 'changefreq': 'monthly'},
        {'url': '/tournaments/add_form', 'priority': '0.7', 'changefreq': 'monthly'},
        {'url': '/tournaments/signup', 'priority': '0.8', 'changefreq': 'weekly'},
        {'url': '/rosters/', 'priority': '0.8', 'changefreq': 'weekly'},
        {'url': '/rosters/upload_roster', 'priority': '0.6', 'changefreq': 'monthly'},
        {'url': '/metrics/', 'priority': '0.7', 'changefreq': 'weekly'},
        {'url': '/metrics/settings', 'priority': '0.5', 'changefreq': 'monthly'},
        {'url': '/admin/', 'priority': '0.6', 'changefreq': 'weekly'},
        {'url': '/admin/requirements', 'priority': '0.5', 'changefreq': 'monthly'},
        {'url': '/admin/events_management', 'priority': '0.6', 'changefreq': 'weekly'},
        {'url': '/admin/search', 'priority': '0.7', 'changefreq': 'daily'},
        {'url': '/admin/test_data', 'priority': '0.3', 'changefreq': 'rarely'},
        {'url': '/admin/delete_management', 'priority': '0.4', 'changefreq': 'monthly'},
    ]
    
    # Get current timestamp in ISO format
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
    
    # Start building the sitemap XML
    sitemap_xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    sitemap_xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    
    # Add static routes
    for route in static_routes:
        sitemap_xml.append('  <url>')
        sitemap_xml.append(f'    <loc>{base_url}{route["url"]}</loc>')
        sitemap_xml.append(f'    <lastmod>{now}</lastmod>')
        sitemap_xml.append(f'    <changefreq>{route["changefreq"]}</changefreq>')
        sitemap_xml.append(f'    <priority>{route["priority"]}</priority>')
        sitemap_xml.append('  </url>')
    
    # Add dynamic routes for events
    try:
        events = Event.query.all()
        for event in events:
            sitemap_xml.append('  <url>')
            sitemap_xml.append(f'    <loc>{base_url}/events/edit_event/{event.id}</loc>')
            sitemap_xml.append(f'    <lastmod>{now}</lastmod>')
            sitemap_xml.append('    <changefreq>weekly</changefreq>')
            sitemap_xml.append('    <priority>0.6</priority>')
            sitemap_xml.append('  </url>')
            
            sitemap_xml.append('  <url>')
            sitemap_xml.append(f'    <loc>{base_url}/events/manage_members/{event.id}</loc>')
            sitemap_xml.append(f'    <lastmod>{now}</lastmod>')
            sitemap_xml.append('    <changefreq>weekly</changefreq>')
            sitemap_xml.append('    <priority>0.5</priority>')
            sitemap_xml.append('  </url>')
    except Exception:
        # If database query fails, skip dynamic event routes
        pass
    
    # Try to add dynamic routes for tournaments
    try:
        from mason_snd.models.tournaments import Tournament
        tournaments = Tournament.query.all()
        for tournament in tournaments:
            sitemap_xml.append('  <url>')
            sitemap_xml.append(f'    <loc>{base_url}/rosters/view_tournament/{tournament.id}</loc>')
            sitemap_xml.append(f'    <lastmod>{now}</lastmod>')
            sitemap_xml.append('    <changefreq>weekly</changefreq>')
            sitemap_xml.append('    <priority>0.7</priority>')
            sitemap_xml.append('  </url>')
    except Exception:
        # If database query fails, skip dynamic tournament routes
        pass
        
    # Try to add dynamic routes for rosters
    try:
        from mason_snd.models.rosters import Roster
        rosters = Roster.query.filter_by(published=True).all()
        for roster in rosters:
            sitemap_xml.append('  <url>')
            sitemap_xml.append(f'    <loc>{base_url}/rosters/view_roster/{roster.id}</loc>')
            sitemap_xml.append(f'    <lastmod>{now}</lastmod>')
            sitemap_xml.append('    <changefreq>monthly</changefreq>')
            sitemap_xml.append('    <priority>0.6</priority>')
            sitemap_xml.append('  </url>')
    except Exception:
        # If database query fails, skip dynamic roster routes
        pass
    
    sitemap_xml.append('</urlset>')
    
    # Join all lines and create response
    xml_content = '\n'.join(sitemap_xml)
    
    response = Response(xml_content, mimetype='application/xml')
    response.headers['Content-Type'] = 'application/xml; charset=utf-8'
    
    return response

@main_bp.route('/robots.txt')
def robots():
    """Generate robots.txt file."""
    base_url = request.url_root.rstrip('/')
    
    robots_content = f"""User-agent: *
Allow: /
Allow: /events/
Allow: /tournaments/
Allow: /rosters/
Disallow: /admin/
Disallow: /profile/
Disallow: /auth/
Disallow: /metrics/

Sitemap: {base_url}/sitemap.xml
"""
    
    response = Response(robots_content, mimetype='text/plain')
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    
    return response