#!/usr/bin/env python3
"""
Quick test to verify favicon route is working
"""
import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from flask import Flask
from mason_snd.blueprints.main.main import main_bp

def test_favicon():
    app = Flask(__name__)
    app.register_blueprint(main_bp)
    
    with app.test_client() as client:
        # Test the favicon route
        response = client.get('/favicon.ico')
        print(f"Favicon route status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Cache-Control: {response.headers.get('Cache-Control')}")
        print(f"Content length: {len(response.data)} bytes")
        
        if response.status_code == 200:
            print("✅ Favicon route is working correctly!")
        else:
            print("❌ Favicon route failed!")
            
        # Test the alternative favicon route
        response2 = client.get('/favicon')
        print(f"\nAlternative favicon route status: {response2.status_code}")
        
        if response2.status_code == 200:
            print("✅ Alternative favicon route is working correctly!")
        else:
            print("❌ Alternative favicon route failed!")

if __name__ == "__main__":
    test_favicon()
