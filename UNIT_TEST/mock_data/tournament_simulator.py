"""
Complete tournament simulation system.
Simulates the entire tournament workflow from registration to results.
"""
import random
from datetime import datetime, timedelta
import pytz
from faker import Faker

fake = Faker()

class TournamentSimulator:
    """Simulates complete tournament workflows with realistic data"""
    
    def __init__(self, app_context=None):
        self.app_context = app_context
        self.simulation_log = []
        
    def log(self, message):
        """Log simulation steps"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.simulation_log.append(f"[{timestamp}] {message}")
        print(f"[SIMULATION] {message}")
    
    def simulate_complete_tournament_flow(self, num_users=30, num_events=5, num_tournaments=2):
        """
        Simulate complete tournament flow from start to finish
        
        Args:
            num_users: Number of users to create
            num_events: Number of events to create
            num_tournaments: Number of tournaments to simulate
            
        Returns:
            dict: Complete simulation results
        """
        self.log("Starting complete tournament flow simulation")
        
        # Step 1: Create users and establish relationships
        users_data = self._create_users_with_relationships(num_users)
        self.log(f"Created {len(users_data['users'])} users with {len(users_data['judge_relationships'])} judge relationships")
        
        # Step 2: Create events and simulate participation
        events_data = self._create_events_with_participation(num_events, users_data['user_ids'])
        self.log(f"Created {len(events_data['events'])} events with participation")
        
        # Step 3: Create tournaments and simulate signups
        tournaments_data = self._create_tournaments_with_signups(num_tournaments, users_data['user_ids'])
        self.log(f"Created {len(tournaments_data['tournaments'])} tournaments with signups")
        
        # Step 4: Generate rosters for tournaments
        rosters_data = self._generate_tournament_rosters(tournaments_data, users_data)
        self.log(f"Generated rosters for {len(rosters_data)} tournaments")
        
        # Step 5: Simulate tournament execution and scoring
        results_data = self._simulate_tournament_execution(tournaments_data, users_data['user_ids'])
        self.log(f"Simulated execution and scoring for {len(results_data)} tournaments")
        
        # Step 6: Calculate metrics and performance data
        metrics_data = self._calculate_comprehensive_metrics(users_data, events_data, tournaments_data, results_data)
        self.log("Calculated comprehensive performance metrics")
        
        simulation_results = {
            'users': users_data,
            'events': events_data,
            'tournaments': tournaments_data,
            'rosters': rosters_data,
            'results': results_data,
            'metrics': metrics_data,
            'simulation_log': self.simulation_log,
            'summary': {
                'total_users': len(users_data['users']),
                'parent_users': len([u for u in users_data['users'] if u['is_parent']]),
                'competitor_users': len([u for u in users_data['users'] if not u['is_parent']]),
                'total_events': len(events_data['events']),
                'total_tournaments': len(tournaments_data['tournaments']),
                'total_signups': sum(len(t['signups']) for t in tournaments_data['tournaments']),
                'simulation_completed': datetime.now().isoformat()
            }
        }
        
        self.log("Tournament flow simulation completed successfully")
        return simulation_results
    
    def _create_users_with_relationships(self, num_users):
        """Create users and establish parent-child judge relationships"""
        from UNIT_TEST.mock_data.generators import MockDataGenerator
        
        generator = MockDataGenerator()
        users = generator.generate_mock_users(num_users)
        
        parent_users = [u for u in users if u['is_parent']]
        competitor_users = [u for u in users if not u['is_parent']]
        
        # Create judge relationships
        judge_relationships = []
        for i, parent in enumerate(parent_users):
            if i < len(competitor_users):
                judge_relationships.append({
                    'parent_user': parent,
                    'child_user': competitor_users[i],
                    'background_check': random.choice([True, True, False]),  # 66% have background check
                    'judging_experience': random.choice(['Novice', 'Experienced', 'Expert'])
                })
        
        return {
            'users': users,
            'parent_users': parent_users,
            'competitor_users': competitor_users,
            'judge_relationships': judge_relationships,
            'user_ids': list(range(1, num_users + 1))
        }
    
    def _create_events_with_participation(self, num_events, user_ids):
        """Create events and simulate user participation"""
        from UNIT_TEST.mock_data.generators import MockDataGenerator
        
        generator = MockDataGenerator()
        events = generator.generate_mock_events(num_events, user_ids)
        
        # Simulate participation for each event
        for i, event in enumerate(events):
            # Random participation rate between 30-80%
            participation_rate = random.uniform(0.3, 0.8)
            participants = random.sample(user_ids, int(len(user_ids) * participation_rate))
            
            event['participants'] = participants
            event['effort_scores'] = []
            
            # Generate effort scores for participants
            for participant_id in participants:
                score = random.randint(5, event['points'])  # Score between 5 and max points
                event['effort_scores'].append({
                    'user_id': participant_id,
                    'event_id': i + 1,
                    'score': score,
                    'feedback': fake.sentence()
                })
        
        return {
            'events': events,
            'total_participations': sum(len(e['participants']) for e in events)
        }
    
    def _create_tournaments_with_signups(self, num_tournaments, user_ids):
        """Create tournaments and simulate realistic signups"""
        from UNIT_TEST.mock_data.generators import MockDataGenerator
        
        generator = MockDataGenerator()
        tournaments = generator.generate_mock_tournaments(num_tournaments, user_ids)
        
        # Simulate signups for each tournament
        for i, tournament in enumerate(tournaments):
            # Tournament signup rate varies (higher for closer tournaments)
            days_until_tournament = (tournament['date'] - datetime.now().date()).days
            if days_until_tournament < 0:  # Past tournament
                signup_rate = 0.6
            elif days_until_tournament < 30:  # Soon
                signup_rate = 0.7
            else:  # Far future
                signup_rate = 0.4
            
            # Select participants
            max_signups = min(tournament.get('max_participants', 50), len(user_ids))
            num_signups = int(max_signups * signup_rate)
            participants = random.sample(user_ids, num_signups)
            
            tournament['signups'] = []
            tournament['judge_requirements'] = []
            
            for participant_id in participants:
                bringing_judge = random.choice([True, False])
                signup_data = {
                    'user_id': participant_id,
                    'tournament_id': i + 1,
                    'signup_date': fake.date_between(
                        start_date=tournament['date'] - timedelta(days=30),
                        end_date=tournament['signup_deadline']
                    ),
                    'bringing_judge': bringing_judge,
                    'partner_preference': random.choice([None, random.choice(participants)]),
                    'dietary_restrictions': random.choice([None, "Vegetarian", "Vegan", "Gluten-free"]),
                    'emergency_contact': fake.phone_number()[:15],
                    'notes': fake.sentence() if random.choice([True, False]) else None
                }
                tournament['signups'].append(signup_data)
                
                # If bringing judge, create judge requirement entry
                if bringing_judge:
                    tournament['judge_requirements'].append({
                        'user_id': participant_id,
                        'tournament_id': i + 1,
                        'rounds_available': random.randint(3, 6),
                        'experience_level': random.choice(['Novice', 'Experienced', 'Expert']),
                        'conflicts': []
                    })
        
        return {
            'tournaments': tournaments,
            'total_signups': sum(len(t['signups']) for t in tournaments)
        }
    
    def _generate_tournament_rosters(self, tournaments_data, users_data):
        """Generate tournament rosters with pairings and judge assignments"""
        rosters = []
        
        for tournament in tournaments_data['tournaments']:
            if not tournament['signups']:
                continue
                
            roster_data = {
                'tournament_id': tournament.get('id', tournaments_data['tournaments'].index(tournament) + 1),
                'tournament_name': tournament['name'],
                'participants': [],
                'pairings': [],
                'judge_assignments': [],
                'rounds': random.randint(4, 6)
            }
            
            # Create participant list
            participants = [signup['user_id'] for signup in tournament['signups']]
            random.shuffle(participants)
            
            # Create pairings (for partner debates)
            for i in range(0, len(participants) - 1, 2):
                if i + 1 < len(participants):
                    pairing = {
                        'team_number': (i // 2) + 1,
                        'debater_1': participants[i],
                        'debater_2': participants[i + 1],
                        'room_assignment': f"Room {random.randint(101, 120)}",
                        'side_preference': random.choice(['Aff', 'Neg', 'No Preference'])
                    }
                    roster_data['pairings'].append(pairing)
            
            # Assign judges
            available_judges = [jr for jr in tournament.get('judge_requirements', [])]
            for round_num in range(1, roster_data['rounds'] + 1):
                round_judges = []
                for pairing in roster_data['pairings'][:len(available_judges)]:
                    if available_judges:
                        judge = random.choice(available_judges)
                        round_judges.append({
                            'round': round_num,
                            'room': pairing['room_assignment'],
                            'judge_user_id': judge['user_id'],
                            'team_1': pairing['team_number'],
                            'team_2': pairing['team_number'] + 1 if pairing['team_number'] < len(roster_data['pairings']) else 1
                        })
                
                roster_data['judge_assignments'].extend(round_judges)
            
            rosters.append(roster_data)
        
        return rosters
    
    def _simulate_tournament_execution(self, tournaments_data, user_ids):
        """Simulate tournament execution with realistic results"""
        results = []
        
        for tournament in tournaments_data['tournaments']:
            if not tournament['signups']:
                continue
                
            tournament_results = {
                'tournament_id': tournaments_data['tournaments'].index(tournament) + 1,
                'tournament_name': tournament['name'],
                'participant_results': [],
                'team_results': [],
                'overall_standings': []
            }
            
            participants = [signup['user_id'] for signup in tournament['signups']]
            
            # Generate individual results
            for rank, user_id in enumerate(random.sample(participants, len(participants)), 1):
                # Realistic scoring based on rank
                base_points = max(0, 100 - (rank - 1) * 3)
                points_variation = random.randint(-5, 15)
                final_points = max(0, base_points + points_variation)
                
                wins = max(0, 6 - rank // 3 + random.randint(-1, 2))
                losses = 6 - wins
                speaker_points = random.uniform(26.0, 29.5)
                
                participant_result = {
                    'user_id': user_id,
                    'rank': rank,
                    'points': final_points,
                    'wins': wins,
                    'losses': losses,
                    'speaker_points': round(speaker_points, 1),
                    'dropped': rank > len(participants) * 0.85 and random.choice([True, False]),  # Some drop out
                    'bid_earned': rank <= 3 and random.choice([True, False]),  # Top performers might earn bids
                    'speaker_award': rank <= 5 and random.choice([True, False, False])  # Speaker awards for top 5
                }
                
                tournament_results['participant_results'].append(participant_result)
            
            # Create overall standings
            tournament_results['overall_standings'] = sorted(
                tournament_results['participant_results'],
                key=lambda x: (-x['points'], -x['wins'], -x['speaker_points'])
            )
            
            results.append(tournament_results)
        
        return results
    
    def _calculate_comprehensive_metrics(self, users_data, events_data, tournaments_data, results_data):
        """Calculate comprehensive performance metrics for all users"""
        metrics = {
            'user_metrics': {},
            'team_metrics': {},
            'overall_statistics': {}
        }
        
        # Calculate individual user metrics
        for user_id in users_data['user_ids']:
            user_metrics = {
                'user_id': user_id,
                'total_tournament_points': 0,
                'total_effort_points': 0,
                'tournaments_attended': 0,
                'events_attended': 0,
                'average_rank': 0,
                'best_rank': float('inf'),
                'total_wins': 0,
                'total_losses': 0,
                'average_speaker_points': 0,
                'bids_earned': 0,
                'speaker_awards': 0,
                'drop_rate': 0
            }
            
            # Tournament metrics
            tournament_performances = []
            for result in results_data:
                for participant in result['participant_results']:
                    if participant['user_id'] == user_id:
                        user_metrics['total_tournament_points'] += participant['points']
                        user_metrics['tournaments_attended'] += 1
                        user_metrics['total_wins'] += participant['wins']
                        user_metrics['total_losses'] += participant['losses']
                        user_metrics['best_rank'] = min(user_metrics['best_rank'], participant['rank'])
                        
                        if participant['bid_earned']:
                            user_metrics['bids_earned'] += 1
                        if participant['speaker_award']:
                            user_metrics['speaker_awards'] += 1
                        if participant['dropped']:
                            user_metrics['drop_rate'] += 1
                        
                        tournament_performances.append(participant)
            
            # Calculate averages
            if tournament_performances:
                user_metrics['average_rank'] = sum(p['rank'] for p in tournament_performances) / len(tournament_performances)
                user_metrics['average_speaker_points'] = sum(p['speaker_points'] for p in tournament_performances) / len(tournament_performances)
                user_metrics['drop_rate'] = user_metrics['drop_rate'] / len(tournament_performances)
            
            # Event metrics
            for event in events_data['events']:
                if user_id in event['participants']:
                    user_metrics['events_attended'] += 1
                    # Find effort score for this user
                    for score in event['effort_scores']:
                        if score['user_id'] == user_id:
                            user_metrics['total_effort_points'] += score['score']
                            break
            
            # Calculate overall performance score
            user_metrics['overall_score'] = (
                user_metrics['total_tournament_points'] + 
                user_metrics['total_effort_points'] * 2
            )
            
            metrics['user_metrics'][user_id] = user_metrics
        
        # Overall statistics
        all_user_metrics = list(metrics['user_metrics'].values())
        metrics['overall_statistics'] = {
            'total_users': len(all_user_metrics),
            'average_tournament_points': sum(m['total_tournament_points'] for m in all_user_metrics) / len(all_user_metrics) if all_user_metrics else 0,
            'average_effort_points': sum(m['total_effort_points'] for m in all_user_metrics) / len(all_user_metrics) if all_user_metrics else 0,
            'total_bids_earned': sum(m['bids_earned'] for m in all_user_metrics),
            'total_speaker_awards': sum(m['speaker_awards'] for m in all_user_metrics),
            'average_drop_rate': sum(m['drop_rate'] for m in all_user_metrics) / len(all_user_metrics) if all_user_metrics else 0,
            'most_active_user': max(all_user_metrics, key=lambda x: x['tournaments_attended'] + x['events_attended'])['user_id'] if all_user_metrics else None,
            'highest_scorer': max(all_user_metrics, key=lambda x: x['overall_score'])['user_id'] if all_user_metrics else None
        }
        
        return metrics
    
    def test_roster_download_upload_workflow(self, roster_data):
        """Test roster download and upload functionality"""
        self.log("Testing roster download/upload workflow")
        
        # Simulate roster download (would generate CSV/Excel)
        download_data = {
            'tournament_name': roster_data['tournament_name'],
            'participant_count': len(roster_data['participants']),
            'pairing_count': len(roster_data['pairings']),
            'judge_count': len(roster_data['judge_assignments']),
            'download_format': 'csv',
            'download_timestamp': datetime.now().isoformat()
        }
        
        # Simulate roster modifications
        modified_data = download_data.copy()
        modified_data['modifications'] = [
            'Added 2 new participants',
            'Modified 3 room assignments',
            'Updated 1 judge assignment',
            'Changed 2 side preferences'
        ]
        modified_data['modification_timestamp'] = datetime.now().isoformat()
        
        # Simulate roster upload and validation
        upload_result = {
            'upload_successful': True,
            'validation_errors': [],
            'warnings': [
                'Judge availability conflict detected',
                'Room capacity might be exceeded'
            ],
            'changes_applied': len(modified_data['modifications']),
            'upload_timestamp': datetime.now().isoformat()
        }
        
        self.log("Roster download/upload workflow test completed")
        return {
            'download': download_data,
            'modifications': modified_data,
            'upload': upload_result
        }

def create_database_with_simulation(simulation_results, test_db_path):
    """Create database with simulation data"""
    try:
        from UNIT_TEST.database_manager import create_test_app
        
        app, _ = create_test_app(test_db_path)
        
        with app.app_context():
            from mason_snd.extensions import db
            from mason_snd.models.auth import User, Judges
            from mason_snd.models.events import Event, User_Event, Effort_Score
            from mason_snd.models.tournaments import Tournament, Tournament_Signups, Tournament_Performance
            
            # Create all tables
            db.create_all()
            
            # Insert users
            created_users = {}
            for i, user_data in enumerate(simulation_results['users']['users']):
                user = User(**user_data)
                db.session.add(user)
                db.session.flush()  # Get ID
                created_users[i + 1] = user.id
            
            # Insert events
            created_events = {}
            for i, event_data in enumerate(simulation_results['events']['events']):
                event_copy = event_data.copy()
                # Remove non-model fields
                event_copy.pop('participants', None)
                event_copy.pop('effort_scores', None)
                
                event = Event(**event_copy)
                db.session.add(event)
                db.session.flush()
                created_events[i + 1] = event.id
                
                # Add participants
                for participant_id in event_data.get('participants', []):
                    if participant_id in created_users:
                        user_event = User_Event(
                            user_id=created_users[participant_id],
                            event_id=event.id
                        )
                        db.session.add(user_event)
                
                # Add effort scores
                for score_data in event_data.get('effort_scores', []):
                    if score_data['user_id'] in created_users:
                        effort_score = Effort_Score(
                            user_id=created_users[score_data['user_id']],
                            event_id=event.id,
                            score=score_data['score']
                        )
                        db.session.add(effort_score)
            
            # Insert tournaments
            created_tournaments = {}
            for i, tournament_data in enumerate(simulation_results['tournaments']['tournaments']):
                tournament_copy = tournament_data.copy()
                # Remove non-model fields
                tournament_copy.pop('signups', None)
                tournament_copy.pop('judge_requirements', None)
                
                tournament = Tournament(**tournament_copy)
                db.session.add(tournament)
                db.session.flush()
                created_tournaments[i + 1] = tournament.id
                
                # Add signups
                for signup_data in tournament_data.get('signups', []):
                    if signup_data['user_id'] in created_users:
                        signup_copy = signup_data.copy()
                        signup_copy['user_id'] = created_users[signup_copy['user_id']]
                        signup_copy['tournament_id'] = tournament.id
                        
                        signup = Tournament_Signups(**signup_copy)
                        db.session.add(signup)
            
            # Insert tournament results
            for result_data in simulation_results['results']:
                tournament_id = created_tournaments.get(result_data['tournament_id'])
                if tournament_id:
                    for participant_result in result_data['participant_results']:
                        if participant_result['user_id'] in created_users:
                            performance = Tournament_Performance(
                                user_id=created_users[participant_result['user_id']],
                                tournament_id=tournament_id,
                                rank=participant_result['rank'],
                                points=participant_result['points'],
                                wins=participant_result['wins'],
                                losses=participant_result['losses'],
                                speaker_points=participant_result['speaker_points']
                            )
                            db.session.add(performance)
            
            # Insert judge relationships
            for judge_rel in simulation_results['users']['judge_relationships']:
                # Find parent and child IDs
                parent_id = None
                child_id = None
                
                for i, user in enumerate(simulation_results['users']['users']):
                    if user == judge_rel['parent_user']:
                        parent_id = created_users[i + 1]
                    elif user == judge_rel['child_user']:
                        child_id = created_users[i + 1]
                
                if parent_id and child_id:
                    judge = Judges(
                        judge_id=parent_id,
                        child_id=child_id,
                        background_check=judge_rel['background_check']
                    )
                    db.session.add(judge)
            
            db.session.commit()
            
            return {
                'success': True,
                'created_users': len(created_users),
                'created_events': len(created_events),
                'created_tournaments': len(created_tournaments),
                'database_path': test_db_path
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # Example usage
    simulator = TournamentSimulator()
    results = simulator.simulate_complete_tournament_flow(
        num_users=20,
        num_events=4,
        num_tournaments=2
    )
    
    print("Simulation completed!")
    print(f"Created {results['summary']['total_users']} users")
    print(f"Created {results['summary']['total_events']} events")
    print(f"Created {results['summary']['total_tournaments']} tournaments")
    print(f"Total signups: {results['summary']['total_signups']}")