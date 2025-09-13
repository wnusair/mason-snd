#!/usr/bin/env python3
"""
Flask development server runner for Mason SND application
"""

from mason_snd import create_app

if __name__ == '__main__':
    app = create_app()
    print("🚀 Starting Mason SND application with Flask-Admin...")
    print("📊 Admin panel will be available at: http://localhost:5000/admin/")
    print("🏠 Main site will be available at: http://localhost:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)
