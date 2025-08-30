#!/usr/bin/env python3
"""
Test script to validate the registration form validation logic.
This script simulates form submission scenarios to test our validation.
"""

def test_parent_validation():
    """Test the parent/child selection validation logic"""
    
    # Simulate form data scenarios
    test_cases = [
        {
            'name': 'No parent selection',
            'form_data': {
                'is_parent': None,  # This is what happens when no radio button is selected
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'phone_number': '555-1234',
                'password': 'password123',
                'confirm_password': 'password123'
            },
            'expected_error': 'Please select whether you are a parent or not.'
        },
        {
            'name': 'Parent with missing child info',
            'form_data': {
                'is_parent': 'yes',
                'first_name': 'Jane',
                'last_name': 'Doe',
                'email': 'jane@example.com',
                'phone_number': '555-5678',
                'password': 'password123',
                'confirm_password': 'password123',
                'child_first_name': '',  # Missing
                'child_last_name': 'Smith'
            },
            'expected_error': "Child's first name and last name are required when registering as a parent."
        },
        {
            'name': 'Student with missing emergency contact info',
            'form_data': {
                'is_parent': 'no',
                'first_name': 'Bob',
                'last_name': 'Smith',
                'email': 'bob@example.com',
                'phone_number': '555-9999',
                'password': 'password123',
                'confirm_password': 'password123',
                'emergency_first_name': 'Mary',
                'emergency_last_name': 'Smith',
                'emergency_email': '',  # Missing
                'emergency_phone': '555-0000',
                'emergency_relationship': 'Mother'
            },
            'expected_error': 'All emergency contact information is required when registering as a student.'
        },
        {
            'name': 'Valid parent registration',
            'form_data': {
                'is_parent': 'yes',
                'first_name': 'Alice',
                'last_name': 'Johnson',
                'email': 'alice@example.com',
                'phone_number': '555-1111',
                'password': 'password123',
                'confirm_password': 'password123',
                'child_first_name': 'Tommy',
                'child_last_name': 'Johnson'
            },
            'expected_error': None
        },
        {
            'name': 'Valid student registration',
            'form_data': {
                'is_parent': 'no',
                'first_name': 'Sarah',
                'last_name': 'Williams',
                'email': 'sarah@example.com',
                'phone_number': '555-2222',
                'password': 'password123',
                'confirm_password': 'password123',
                'emergency_first_name': 'David',
                'emergency_last_name': 'Williams',
                'emergency_email': 'david@example.com',
                'emergency_phone': '555-3333',
                'emergency_relationship': 'Father'
            },
            'expected_error': None
        }
    ]
    
    # Test each scenario
    for test_case in test_cases:
        print(f"\n--- Testing: {test_case['name']} ---")
        error = validate_registration_form(test_case['form_data'])
        
        if test_case['expected_error']:
            if error == test_case['expected_error']:
                print(f"✅ PASS: Got expected error: {error}")
            else:
                print(f"❌ FAIL: Expected '{test_case['expected_error']}', got '{error}'")
        else:
            if error is None:
                print("✅ PASS: Valid form data accepted")
            else:
                print(f"❌ FAIL: Expected no error, got '{error}'")

def validate_registration_form(form_data):
    """
    Simulates the validation logic from our auth.py registration route
    """
    # Extract form data
    first_name = form_data.get('first_name')
    last_name = form_data.get('last_name')
    email = form_data.get('email')
    phone_number = form_data.get('phone_number')
    is_parent_form_value = form_data.get('is_parent')
    password = form_data.get('password')
    confirm_password = form_data.get('confirm_password')

    # Validate basic required fields
    if not all([first_name, last_name, email, phone_number, password, confirm_password]):
        return "All basic information fields are required."

    # Validate that is_parent is actually selected
    if is_parent_form_value not in ['yes', 'no']:
        return "Please select whether you are a parent or not."

    is_parent = is_parent_form_value == 'yes'

    if is_parent:
        child_first_name = form_data.get('child_first_name')
        child_last_name = form_data.get('child_last_name')
        
        # Validate required child information
        if not child_first_name or not child_last_name:
            return "Child's first name and last name are required when registering as a parent."
    else:
        emergency_first_name = form_data.get('emergency_first_name')
        emergency_last_name = form_data.get('emergency_last_name')
        emergency_email = form_data.get('emergency_email')
        emergency_phone = form_data.get('emergency_phone')
        emergency_relationship = form_data.get('emergency_relationship')
        
        # Validate required emergency contact information
        if not all([emergency_first_name, emergency_last_name, emergency_email, emergency_phone, emergency_relationship]):
            return "All emergency contact information is required when registering as a student."

    # Validate password match
    if password != confirm_password:
        return "Passwords do not match"

    return None  # No errors

if __name__ == "__main__":
    print("🧪 Testing Registration Form Validation Logic")
    print("=" * 50)
    test_parent_validation()
    print("\n" + "=" * 50)
    print("✅ Testing complete!")
