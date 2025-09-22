"""
Roster functionality testing module.
Tests roster generation, download, upload, and validation workflows.
"""
import csv
import io
import json
import tempfile
import os
from datetime import datetime
from flask import current_app

class RosterTester:
    """Tests roster-related functionality comprehensively"""
    
    def __init__(self, app_context=None):
        self.app_context = app_context
        self.test_results = []
    
    def log_test(self, test_name, success, details=None):
        """Log test results"""
        result = {
            'test_name': test_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"[ROSTER TEST] {status}: {test_name}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_roster_generation(self, tournament_data, participants):
        """Test tournament roster generation"""
        try:
            # Simulate roster generation logic
            roster = {
                'tournament_id': tournament_data.get('id', 1),
                'tournament_name': tournament_data['name'],
                'date': tournament_data['date'].isoformat() if hasattr(tournament_data['date'], 'isoformat') else str(tournament_data['date']),
                'participants': [],
                'pairings': [],
                'judge_assignments': [],
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_participants': len(participants),
                    'estimated_rounds': max(4, len(participants) // 8)
                }
            }
            
            # Create participant entries
            for i, participant_id in enumerate(participants):
                roster['participants'].append({
                    'participant_id': participant_id,
                    'entry_number': i + 1,
                    'status': 'confirmed',
                    'special_needs': None
                })
            
            # Create pairings
            paired_participants = participants.copy()
            while len(paired_participants) >= 2:
                debater1 = paired_participants.pop(0)
                debater2 = paired_participants.pop(0) if paired_participants else None
                
                if debater2:
                    pairing = {
                        'team_id': len(roster['pairings']) + 1,
                        'debater_1': debater1,
                        'debater_2': debater2,
                        'room': f"Room {100 + len(roster['pairings']) + 1}",
                        'side_assignment': 'TBD'
                    }
                    roster['pairings'].append(pairing)
            
            # Handle odd participant
            if paired_participants:
                # Bye or triple
                roster['special_cases'] = [
                    {'type': 'bye', 'participant': paired_participants[0]}
                ]
            
            self.log_test("Roster Generation", True, {
                'participants_processed': len(participants),
                'pairings_created': len(roster['pairings']),
                'special_cases': len(roster.get('special_cases', []))
            })
            
            return roster
            
        except Exception as e:
            self.log_test("Roster Generation", False, {'error': str(e)})
            return None
    
    def test_roster_download(self, roster_data, format_type='csv'):
        """Test roster download functionality"""
        try:
            if format_type.lower() == 'csv':
                return self._test_csv_download(roster_data)
            elif format_type.lower() == 'json':
                return self._test_json_download(roster_data)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            self.log_test(f"Roster Download ({format_type})", False, {'error': str(e)})
            return None
    
    def _test_csv_download(self, roster_data):
        """Test CSV roster download"""
        try:
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Team ID', 'Debater 1 ID', 'Debater 2 ID', 
                'Room Assignment', 'Side Assignment', 'Status'
            ])
            
            # Write pairings
            for pairing in roster_data.get('pairings', []):
                writer.writerow([
                    pairing['team_id'],
                    pairing['debater_1'],
                    pairing['debater_2'],
                    pairing['room'],
                    pairing.get('side_assignment', 'TBD'),
                    'Active'
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            # Validate CSV content
            lines = csv_content.strip().split('\n')
            expected_lines = len(roster_data.get('pairings', [])) + 1  # +1 for header
            
            if len(lines) == expected_lines:
                self.log_test("CSV Download", True, {
                    'lines_generated': len(lines),
                    'content_size': len(csv_content)
                })
                return csv_content
            else:
                raise ValueError(f"Expected {expected_lines} lines, got {len(lines)}")
                
        except Exception as e:
            self.log_test("CSV Download", False, {'error': str(e)})
            return None
    
    def _test_json_download(self, roster_data):
        """Test JSON roster download"""
        try:
            json_content = json.dumps(roster_data, indent=2, default=str)
            
            # Validate JSON
            parsed = json.loads(json_content)
            
            required_fields = ['tournament_id', 'tournament_name', 'participants', 'pairings']
            missing_fields = [field for field in required_fields if field not in parsed]
            
            if not missing_fields:
                self.log_test("JSON Download", True, {
                    'content_size': len(json_content),
                    'participants': len(parsed.get('participants', [])),
                    'pairings': len(parsed.get('pairings', []))
                })
                return json_content
            else:
                raise ValueError(f"Missing required fields: {missing_fields}")
                
        except Exception as e:
            self.log_test("JSON Download", False, {'error': str(e)})
            return None
    
    def test_roster_upload(self, original_roster, modified_content, format_type='csv'):
        """Test roster upload and validation"""
        try:
            if format_type.lower() == 'csv':
                return self._test_csv_upload(original_roster, modified_content)
            elif format_type.lower() == 'json':
                return self._test_json_upload(original_roster, modified_content)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            self.log_test(f"Roster Upload ({format_type})", False, {'error': str(e)})
            return None
    
    def _test_csv_upload(self, original_roster, csv_content):
        """Test CSV roster upload"""
        try:
            # Parse CSV content
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            uploaded_pairings = []
            validation_errors = []
            warnings = []
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because of header
                try:
                    pairing = {
                        'team_id': int(row['Team ID']),
                        'debater_1': int(row['Debater 1 ID']),
                        'debater_2': int(row['Debater 2 ID']),
                        'room': row['Room Assignment'],
                        'side_assignment': row['Side Assignment'],
                        'status': row.get('Status', 'Active')
                    }
                    uploaded_pairings.append(pairing)
                    
                    # Validation checks
                    if pairing['debater_1'] == pairing['debater_2']:
                        validation_errors.append(f"Row {row_num}: Debater cannot debate themselves")
                    
                    if not pairing['room'].strip():
                        warnings.append(f"Row {row_num}: Empty room assignment")
                    
                except (ValueError, KeyError) as e:
                    validation_errors.append(f"Row {row_num}: Invalid data - {str(e)}")
            
            # Compare with original
            changes_detected = len(uploaded_pairings) != len(original_roster.get('pairings', []))
            
            upload_result = {
                'success': len(validation_errors) == 0,
                'pairings_processed': len(uploaded_pairings),
                'validation_errors': validation_errors,
                'warnings': warnings,
                'changes_detected': changes_detected,
                'uploaded_pairings': uploaded_pairings
            }
            
            self.log_test("CSV Upload", upload_result['success'], {
                'pairings_processed': upload_result['pairings_processed'],
                'errors': len(validation_errors),
                'warnings': len(warnings)
            })
            
            return upload_result
            
        except Exception as e:
            self.log_test("CSV Upload", False, {'error': str(e)})
            return None
    
    def _test_json_upload(self, original_roster, json_content):
        """Test JSON roster upload"""
        try:
            # Parse JSON content
            uploaded_data = json.loads(json_content)
            
            validation_errors = []
            warnings = []
            
            # Validate structure
            required_fields = ['tournament_id', 'participants', 'pairings']
            for field in required_fields:
                if field not in uploaded_data:
                    validation_errors.append(f"Missing required field: {field}")
            
            # Validate pairings
            for i, pairing in enumerate(uploaded_data.get('pairings', [])):
                if 'debater_1' not in pairing or 'debater_2' not in pairing:
                    validation_errors.append(f"Pairing {i+1}: Missing debater assignments")
                
                if pairing.get('debater_1') == pairing.get('debater_2'):
                    validation_errors.append(f"Pairing {i+1}: Debater cannot debate themselves")
            
            # Check for changes
            original_pairing_count = len(original_roster.get('pairings', []))
            uploaded_pairing_count = len(uploaded_data.get('pairings', []))
            changes_detected = original_pairing_count != uploaded_pairing_count
            
            upload_result = {
                'success': len(validation_errors) == 0,
                'validation_errors': validation_errors,
                'warnings': warnings,
                'changes_detected': changes_detected,
                'uploaded_data': uploaded_data
            }
            
            self.log_test("JSON Upload", upload_result['success'], {
                'pairings_processed': uploaded_pairing_count,
                'errors': len(validation_errors),
                'warnings': len(warnings)
            })
            
            return upload_result
            
        except Exception as e:
            self.log_test("JSON Upload", False, {'error': str(e)})
            return None
    
    def test_roster_validation(self, roster_data, participant_list):
        """Test comprehensive roster validation"""
        try:
            validation_results = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'statistics': {}
            }
            
            # Check participant coverage
            roster_participants = set()
            for pairing in roster_data.get('pairings', []):
                roster_participants.add(pairing['debater_1'])
                roster_participants.add(pairing['debater_2'])
            
            expected_participants = set(participant_list)
            missing_participants = expected_participants - roster_participants
            extra_participants = roster_participants - expected_participants
            
            if missing_participants:
                validation_results['errors'].append(f"Missing participants: {list(missing_participants)}")
                validation_results['valid'] = False
            
            if extra_participants:
                validation_results['warnings'].append(f"Unexpected participants: {list(extra_participants)}")
            
            # Check for duplicate assignments
            all_assignments = []
            for pairing in roster_data.get('pairings', []):
                all_assignments.extend([pairing['debater_1'], pairing['debater_2']])
            
            duplicates = [p for p in set(all_assignments) if all_assignments.count(p) > 1]
            if duplicates:
                validation_results['errors'].append(f"Participants assigned multiple times: {duplicates}")
                validation_results['valid'] = False
            
            # Check room assignments
            rooms = [p['room'] for p in roster_data.get('pairings', [])]
            duplicate_rooms = [r for r in set(rooms) if rooms.count(r) > 1]
            if duplicate_rooms:
                validation_results['warnings'].append(f"Duplicate room assignments: {duplicate_rooms}")
            
            # Statistics
            validation_results['statistics'] = {
                'total_participants': len(roster_participants),
                'total_pairings': len(roster_data.get('pairings', [])),
                'unique_rooms': len(set(rooms)),
                'coverage_percentage': (len(roster_participants) / len(expected_participants)) * 100 if expected_participants else 0
            }
            
            self.log_test("Roster Validation", validation_results['valid'], {
                'errors': len(validation_results['errors']),
                'warnings': len(validation_results['warnings']),
                'coverage': f"{validation_results['statistics']['coverage_percentage']:.1f}%"
            })
            
            return validation_results
            
        except Exception as e:
            self.log_test("Roster Validation", False, {'error': str(e)})
            return None
    
    def test_complete_roster_workflow(self, tournament_data, participants):
        """Test complete roster workflow from generation to validation"""
        workflow_results = {
            'stages_completed': [],
            'overall_success': True,
            'stage_results': {}
        }
        
        try:
            # Stage 1: Generate roster
            roster = self.test_roster_generation(tournament_data, participants)
            if roster:
                workflow_results['stages_completed'].append('generation')
                workflow_results['stage_results']['generation'] = roster
            else:
                workflow_results['overall_success'] = False
                return workflow_results
            
            # Stage 2: Download as CSV
            csv_content = self.test_roster_download(roster, 'csv')
            if csv_content:
                workflow_results['stages_completed'].append('csv_download')
                workflow_results['stage_results']['csv_download'] = len(csv_content)
            else:
                workflow_results['overall_success'] = False
            
            # Stage 3: Download as JSON
            json_content = self.test_roster_download(roster, 'json')
            if json_content:
                workflow_results['stages_completed'].append('json_download')
                workflow_results['stage_results']['json_download'] = len(json_content)
            else:
                workflow_results['overall_success'] = False
            
            # Stage 4: Simulate modifications and upload
            if csv_content:
                # Simulate CSV modification (add a comment or change room)
                modified_csv = csv_content.replace('Room 101', 'Room 201')
                upload_result = self.test_roster_upload(roster, modified_csv, 'csv')
                if upload_result and upload_result['success']:
                    workflow_results['stages_completed'].append('csv_upload')
                    workflow_results['stage_results']['csv_upload'] = upload_result
                else:
                    workflow_results['overall_success'] = False
            
            # Stage 5: Validate final roster
            validation_result = self.test_roster_validation(roster, participants)
            if validation_result and validation_result['valid']:
                workflow_results['stages_completed'].append('validation')
                workflow_results['stage_results']['validation'] = validation_result
            else:
                workflow_results['overall_success'] = False
            
            self.log_test("Complete Roster Workflow", workflow_results['overall_success'], {
                'stages_completed': len(workflow_results['stages_completed']),
                'total_stages': 5
            })
            
            return workflow_results
            
        except Exception as e:
            self.log_test("Complete Roster Workflow", False, {'error': str(e)})
            workflow_results['overall_success'] = False
            return workflow_results
    
    def get_test_summary(self):
        """Get summary of all roster tests"""
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['success']])
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            'test_details': self.test_results
        }

# Helper function for integration with main testing system
def run_roster_tests(tournament_data, participants):
    """Run all roster tests and return results"""
    tester = RosterTester()
    
    # Run complete workflow test
    workflow_results = tester.test_complete_roster_workflow(tournament_data, participants)
    
    # Get summary
    summary = tester.get_test_summary()
    
    return {
        'workflow_results': workflow_results,
        'test_summary': summary,
        'detailed_results': tester.test_results
    }

if __name__ == "__main__":
    # Example usage
    sample_tournament = {
        'id': 1,
        'name': 'Test Tournament',
        'date': datetime.now().date()
    }
    
    sample_participants = [1, 2, 3, 4, 5, 6, 7, 8]
    
    results = run_roster_tests(sample_tournament, sample_participants)
    print(f"Roster tests completed with {results['test_summary']['success_rate']:.1f}% success rate")