#!/usr/bin/env python
"""
Final test for tournament-specific signup download functionality.
Tests actual Excel generation without requiring a web browser.
"""

import sys
import os
import tempfile
from io import BytesIO

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.tournaments import Tournament, Tournament_Signups
from mason_snd.models.auth import User
from mason_snd.models.events import Event

def test_excel_generation():
    """Test that we can generate Excel files for tournament signups"""
    print("\n" + "="*70)
    print("TESTING EXCEL GENERATION FOR TOURNAMENT SIGNUPS")
    print("="*70 + "\n")
    
    app = create_app()
    
    with app.app_context():
        # Import Excel dependencies
        try:
            import pandas as pd
            import openpyxl
            from openpyxl.styles import PatternFill, Font, Alignment
            print("✓ Excel dependencies (pandas, openpyxl) are available")
        except ImportError as e:
            print(f"❌ Missing Excel dependencies: {e}")
            return False
        
        # Get tournament data
        tournament = Tournament.query.first()
        if not tournament:
            print("❌ No tournaments found in database")
            return False
            
        print(f"✓ Testing with tournament: {tournament.name} (ID: {tournament.id})")
        
        # Get signups for this tournament
        signups = Tournament_Signups.query.filter_by(tournament_id=tournament.id).all()
        print(f"✓ Found {len(signups)} signups for this tournament")
        
        if not signups:
            print("❌ No signups found for tournament")
            return False
        
        # Test data processing (same logic as in the route)
        print("\n📊 Processing signup data...")
        signup_data = []
        
        for i, signup in enumerate(signups[:5]):  # Test with first 5 for speed
            # Get user information
            user_obj = User.query.get(signup.user_id) if signup.user_id else None
            user_name = f"{user_obj.first_name} {user_obj.last_name}" if user_obj else 'Unknown'
            user_email = user_obj.email if user_obj else ''
            
            # Tournament information
            tournament_name = tournament.name
            tournament_date = tournament.date.strftime('%Y-%m-%d %H:%M') if tournament.date else ''
            
            # Get event information
            event = Event.query.get(signup.event_id) if signup.event_id else None
            event_name = event.event_name if event else 'Unknown Event'
            
            # Determine event type/category
            event_type = 'Unknown'
            if event:
                if event.event_type == 0:
                    event_type = 'Speech'
                elif event.event_type == 1:
                    event_type = 'LD'
                elif event.event_type == 2:
                    event_type = 'PF'
            
            # Get judge information
            judge = User.query.get(signup.judge_id) if signup.judge_id and signup.judge_id != 0 else None
            judge_name = f"{judge.first_name} {judge.last_name}" if judge else ''
            
            # Get partner information
            partner = User.query.get(signup.partner_id) if signup.partner_id else None
            partner_name = f"{partner.first_name} {partner.last_name}" if partner else ''
            
            signup_data.append({
                'Signup ID': signup.id,
                'Tournament Name': tournament_name,
                'Tournament Date': tournament_date,
                'Student Name': user_name,
                'Student Email': user_email,
                'Event Name': event_name,
                'Event Category': event_type,
                'Partner Name': partner_name,
                'Bringing Judge': 'Yes' if signup.bringing_judge else 'No',
                'Judge Name': judge_name,
                'Is Going': 'Yes' if signup.is_going else 'No',
                'User ID': signup.user_id,
                'Tournament ID': signup.tournament_id,
                'Event ID': signup.event_id,
                'Judge ID': signup.judge_id if signup.judge_id and signup.judge_id != 0 else '',
                'Partner ID': signup.partner_id if signup.partner_id else ''
            })
            
            print(f"  ✓ Processed signup {i+1}: {user_name} -> {event_name}")
        
        print(f"\n📝 Creating Excel file...")
        
        # Create DataFrame
        df = pd.DataFrame(signup_data)
        print(f"  ✓ Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
        
        # Create Excel file in memory
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        
        # Write to Excel with formatting
        sheet_name = f'{tournament.name} Signups'
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"  ✓ Wrote data to Excel sheet: '{sheet_name}'")
        
        # Get the workbook and worksheet for styling
        workbook = writer.book
        worksheet = workbook.active
        
        # Style the header row
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        print(f"  ✓ Applied header styling")
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        print(f"  ✓ Auto-adjusted column widths")
        
        writer.close()
        output.seek(0)
        
        # Test file size and content
        file_size = len(output.getvalue())
        print(f"  ✓ Generated Excel file size: {file_size} bytes")
        
        # Generate filename
        safe_tournament_name = "".join(c for c in tournament.name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_tournament_name = safe_tournament_name.replace(' ', '_')
        filename = f"{safe_tournament_name}_signups_test.xlsx"
        print(f"  ✓ Generated filename: {filename}")
        
        # Optional: Save file for manual inspection
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, filename)
        
        with open(temp_file_path, 'wb') as f:
            f.write(output.getvalue())
        
        print(f"  ✓ Test file saved to: {temp_file_path}")
        print(f"  📁 You can open this file to verify the Excel formatting")
        
        print(f"\n✅ Excel generation test completed successfully!")
        print(f"\n📋 VERIFICATION CHECKLIST:")
        print(f"  ✅ Excel dependencies available")
        print(f"  ✅ Tournament data retrieved")
        print(f"  ✅ Signup data processed")
        print(f"  ✅ DataFrame created")
        print(f"  ✅ Excel file generated")
        print(f"  ✅ Header styling applied")
        print(f"  ✅ Column widths optimized")
        print(f"  ✅ File saved successfully")
        
        return True

if __name__ == "__main__":
    try:
        success = test_excel_generation()
        if success:
            print(f"\n🎉 SUCCESS: Excel generation is working perfectly!")
        else:
            print(f"\n❌ FAILED: Excel generation encountered issues")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)