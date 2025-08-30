#!/usr/bin/env python3
"""
Debug the registration form to see what's causing the 400 errors
"""

import os
import sys
sys.path.insert(0, '/home/wnusair/mason-snd')

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges

def debug_registration():
    """Debug registration form submission"""
    
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            print("=== Testing registration form directly ===")
            
            # First, let's see if the route exists
            response = client.get('/auth/register')
            print(f"GET /auth/register status: {response.status_code}")
            
            if response.status_code == 200:
                print("Registration form loads successfully")
            
            # Try a simple registration with minimal validation
            simple_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone_number': '555-0000',
                'is_parent': 'no',
                'emergency_first_name': 'Emergency',
                'emergency_last_name': 'Contact',
                'emergency_email': 'emergency@example.com',
                'emergency_phone': '555-1111',
                'emergency_relationship': 'parent',
                'password': 'testpass',
                'confirm_password': 'testpass'
            }
            
            print("\n=== Attempting simple registration ===")
            response = client.post('/auth/register', data=simple_data, follow_redirects=True)
            print(f"POST /auth/register status: {response.status_code}")
            print(f"Response data length: {len(response.data)}")
            
            # Check if user was created
            user = User.query.filter_by(first_name='test', last_name='user').first()
            if user:
                print(f"User created successfully: ID={user.id}")
            else:
                print("No user was created")
                
            # Let's try to see the response content (first 500 chars)
            if response.data:
                content = response.data.decode('utf-8')[:500]
                print(f"Response content preview: {content}")

if __name__ == '__main__':
    debug_registration()
