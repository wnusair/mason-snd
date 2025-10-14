"""Main Blueprint - Landing pages, SEO, and static file serving.

Handles the application's main entry points, static resource serving (favicon),
and SEO optimization features (sitemap.xml, robots.txt). Provides core navigation
and informational pages.

Route Organization:
    Landing Pages:
        - index(): Main homepage with login redirect
        - life(): Informational "Life" page
    
    Static Resources:
        - favicon(): Serve favicon.ico from static directory
    
    SEO Features:
        - sitemap(): Generate XML sitemap for search engines
        - robots(): Generate robots.txt for crawler instructions

SEO Implementation:
    Sitemap Generation:
        - Dynamic XML sitemap with all application routes
        - Includes static routes (login, register, events, tournaments, etc.)
        - Includes dynamic routes (individual events, tournaments, rosters)
        - Priority and change frequency metadata for each URL
        - Last modified timestamps in ISO 8601 format
        - Graceful error handling for database queries
    
    Robots.txt:
        - Allows public pages (events, tournaments, rosters)
        - Disallows private pages (admin, profile, auth, metrics)
        - Points to sitemap.xml for crawler discovery
    
    Favicon Serving:
        - Serves icon.png as favicon
        - Includes cache headers (1 day TTL)
        - Handles both /favicon.ico and /favicon routes

Key Features:
    - Automatic redirect for logged-in users (homepage → profile)
    - Comprehensive sitemap with static and dynamic routes
    - SEO-friendly robots.txt configuration
    - Proper cache headers for static resources
    - Error handling for missing files and database failures
"""

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
    """Main homepage with automatic profile redirect for logged-in users.
    
    Displays the public landing page for anonymous users. Automatically redirects
    authenticated users to their profile page for faster navigation.
    
    Behavior:
        Not Logged In:
            - Displays main/index.html (public homepage)
            - Likely shows app description, features, login/register links
        
        Logged In:
            - Redirects to profile.index with current user_id
            - Bypasses homepage for returning users
            - Provides direct access to personalized profile
    
    Session Data:
        - Reads 'user_id' from session
        - No modification to session
    
    Template Variables:
        - user_id: Current user ID or None (for navbar state)
    
    Returns:
        If logged in: Redirect to profile.index(user_id).
        If not logged in: Renders main/index.html.
    
    Note:
        This auto-redirect pattern improves UX by skipping the public homepage
        for authenticated users who want to access their profile quickly.
    """
    user_id = session.get('user_id')

    if user_id is not None:
        return redirect(url_for('profile.index', user_id=user_id))

    return render_template('main/index.html', user_id=user_id)

@main_bp.route('/life')
def life():
    """Display informational 'Life' page.
    
    Renders a static informational page, likely containing information about
    the organization, mission, values, or other contextual content.
    
    Access:
        Public (no authentication required).
    
    Returns:
        Renders main/life.html template.
    
    Note:
        Content and purpose defined by template. May include organization
        history, mission statement, community guidelines, or similar content.
    """
    return render_template('main/life.html')

@main_bp.route('/favicon.ico')
@main_bp.route('/favicon')
def favicon():
    """Serve favicon from static directory with caching.
    
    Serves the application's favicon (icon.png) with proper cache headers
    to minimize repeated requests. Handles both /favicon.ico (standard) and
    /favicon (custom) routes.
    
    File Location:
        - Path: mason_snd/static/icon.png
        - Resolved dynamically from blueprint directory
        - Three levels up from main.py: main/ → blueprints/ → mason_snd/
    
    Cache Headers:
        - Cache-Control: public, max-age=86400 (1 day)
        - Expires: Wed, 31 Dec 2025 23:59:59 GMT (far future)
        - Purpose: Reduce server load from repeated favicon requests
    
    Error Handling:
        - Returns 404 if icon.png not found
        - Logs error to current_app.logger
        - Provides file path in error message for debugging
    
    MIME Type:
        image/png (icon.png format, not .ico)
    
    Returns:
        Success: Sends icon.png with cache headers.
        Failure: Returns "Favicon not found", 404.
    
    Note:
        Using PNG instead of ICO format. Modern browsers support both.
        Cache headers prevent repeated requests during user session.
    """
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
    """Generate dynamic XML sitemap for search engine optimization.
    
    Creates a comprehensive sitemap.xml file containing all public application
    routes with SEO metadata (priority, change frequency, last modified).
    Includes both static routes and dynamic routes (events, tournaments, rosters).
    
    Sitemap Structure:
        Static Routes:
            - Homepage, life page
            - Auth routes (login, register, logout)
            - Events, tournaments, rosters listing pages
            - Admin pages (for completeness, but disallowed in robots.txt)
            - Metrics pages
        
        Dynamic Routes:
            - Individual event pages: /events/edit_event/{id}
            - Event member management: /events/manage_members/{id}
            - Tournament rosters: /rosters/view_tournament/{id}
            - Published rosters: /rosters/view_roster/{id}
    
    SEO Metadata:
        Priority (0.0 - 1.0):
            - 1.0: Homepage (highest)
            - 0.9: Events/tournaments listings
            - 0.8: Login, register, tournament signup
            - 0.7: Add tournament, metrics, tournament rosters
            - 0.6: Published rosters, admin pages, event pages
            - 0.5: Settings, requirements, event members
            - 0.3-0.4: Logout, test data, delete management
        
        Change Frequency:
            - daily: Homepage, admin search
            - weekly: Events, tournaments, rosters, admin pages
            - monthly: Auth, settings, static pages
            - rarely: Test data
    
    Dynamic Route Generation:
        Events:
            - Queries all Event records
            - Creates edit_event and manage_members URLs
            - Priority: 0.6 (edit), 0.5 (members)
            - Change frequency: weekly
        
        Tournaments:
            - Queries all Tournament records
            - Creates view_tournament URLs
            - Priority: 0.7
            - Change frequency: weekly
        
        Rosters:
            - Queries published Roster records only
            - Creates view_roster URLs
            - Priority: 0.6
            - Change frequency: monthly
    
    Error Handling:
        - Database queries wrapped in try/except
        - If query fails, skips that section of dynamic routes
        - Ensures sitemap always generated (degraded, not failed)
    
    XML Format:
        - XML declaration: <?xml version="1.0" encoding="UTF-8"?>
        - Namespace: http://www.sitemaps.org/schemas/sitemap/0.9
        - Each URL includes: loc, lastmod, changefreq, priority
        - Last modified: Current UTC timestamp in ISO 8601 format
    
    Response Headers:
        - Content-Type: application/xml; charset=utf-8
        - MIME type: application/xml
    
    Returns:
        XML sitemap as Response object.
    
    Benefits:
        - Helps search engines discover all pages
        - Provides crawling priority hints
        - Updates automatically as content added
        - Includes only public/relevant pages
    
    Note:
        Base URL derived from request.url_root (supports multiple domains).
        All timestamps use current time (not actual last modification).
        Dynamic imports (Tournament, Roster) avoid circular imports.
    """
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
    """Generate robots.txt file for search engine crawler instructions.
    
    Creates robots.txt file that instructs search engine crawlers which pages
    to index (Allow) and which to avoid (Disallow). Protects private areas
    while exposing public content.
    
    Allowed Paths (Public Content):
        - /: Homepage
        - /events/: All event pages
        - /tournaments/: All tournament pages
        - /rosters/: All roster pages
    
    Disallowed Paths (Private Content):
        - /admin/: Administrative interface (sensitive)
        - /profile/: User profiles (privacy)
        - /auth/: Authentication pages (no SEO value)
        - /metrics/: Analytics pages (internal use)
    
    Sitemap Reference:
        - Points crawlers to /sitemap.xml for complete URL list
        - Base URL derived from request.url_root (multi-domain support)
    
    Response Headers:
        - Content-Type: text/plain; charset=utf-8
        - MIME type: text/plain
    
    Returns:
        robots.txt content as plain text Response.
    
    Crawler Scope:
        - User-agent: * (applies to all crawlers)
        - No crawler-specific rules (universal)
    
    Benefits:
        - Prevents indexing of private pages (security, privacy)
        - Focuses crawler budget on valuable public content
        - Prevents duplicate content issues (auth pages)
        - Protects admin interface from discovery
    
    Note:
        robots.txt is advisory only (malicious crawlers may ignore).
        Real security enforced by authentication/authorization.
        Sitemap helps compliant crawlers discover allowed pages efficiently.
    """
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