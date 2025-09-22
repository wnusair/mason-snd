"""
Mock data generators for comprehensive testing.
Creates realistic test data for users, events, tournaments, and more.
"""
import random
from datetime import datetime, timedelta
import pytz
from faker import Faker

fake = Faker()

class MockDataGenerator:
    """Generates realistic mock data for testing"""
    
    def __init__(self, app_context=None):
        self.app_context = app_context
        self.created_users = []
        self.created_events = []
        self.created_tournaments = []
        self.created_judges = []
    
    def generate_mock_users(self, count=20, include_parents=True, include_children=True):
        """
        Generate mock users with realistic data
        
        Args:
            count: Number of users to create
            include_parents: Whether to create parent accounts
            include_children: Whether to create child/competitor accounts
            
        Returns:
            list: Created user data dictionaries
        """
        users = []
        
        for i in range(count):
            is_parent = random.choice([True, False]) if include_parents and include_children else include_parents
            
            if is_parent:
                user_data = self._generate_parent_user()
            else:
                user_data = self._generate_competitor_user()
            
            users.append(user_data)
        
        self.created_users = users
        return users
    
    def _generate_parent_user(self):
        """Generate a parent user with judge capabilities"""
        first_name = fake.first_name()
        last_name = fake.last_name()
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'email': fake.email(),
            'password': 'testpassword123',  # Standard test password
            'phone_number': fake.phone_number()[:15],  # Truncate to fit DB
            'is_parent': True,
            'role': random.choice([0, 1]),  # Member or EL
            'judging_reqs': self._generate_judging_requirements(),
            'emergency_contact_first_name': fake.first_name(),
            'emergency_contact_last_name': fake.last_name(),
            'emergency_contact_number': fake.phone_number()[:15],
            'emergency_contact_relationship': random.choice(['Spouse', 'Parent', 'Sibling', 'Friend']),
            'emergency_contact_email': fake.email(),
            'child_first_name': fake.first_name(),
            'child_last_name': last_name,  # Usually same as parent
            'points': random.randint(0, 100),
            'drops': random.randint(0, 3),
            'bids': random.randint(0, 5),
            'tournaments_attended_number': random.randint(0, 10),
            'account_claimed': True
        }
    
    def _generate_competitor_user(self):
        """Generate a competitor/child user"""
        first_name = fake.first_name()
        last_name = fake.last_name()
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'email': fake.email(),
            'password': 'testpassword123',
            'phone_number': fake.phone_number()[:15],
            'is_parent': False,
            'role': 0,  # Member
            'emergency_contact_first_name': fake.first_name(),
            'emergency_contact_last_name': fake.last_name(),
            'emergency_contact_number': fake.phone_number()[:15],
            'emergency_contact_relationship': 'Parent',
            'emergency_contact_email': fake.email(),
            'points': random.randint(10, 200),
            'drops': random.randint(0, 5),
            'bids': random.randint(0, 8),
            'tournaments_attended_number': random.randint(1, 15),
            'account_claimed': random.choice([True, False])
        }
    
    def _generate_judging_requirements(self):
        """Generate realistic judging requirements text"""
        requirements = [
            "Certified in Public Forum debate judging",
            "3+ years judging experience",
            "NSDA certified judge",
            "Local circuit judging experience",
            "College debate background",
            "Professional experience in argumentation"
        ]
        
        return "; ".join(random.sample(requirements, random.randint(1, 3)))
    
    def generate_mock_events(self, count=5, user_ids=None):
        """
        Generate mock events for testing
        
        Args:
            count: Number of events to create
            user_ids: List of user IDs to assign as event leaders
            
        Returns:
            list: Created event data dictionaries
        """
        event_types = [
            "Weekly Practice", "Mock Tournament", "Debate Workshop", 
            "Research Session", "Speech Practice", "Argumentation Clinic",
            "Evidence Review", "Case Writing Workshop"
        ]
        
        events = []
        
        for i in range(count):
            start_date = fake.date_between(start_date='-30d', end_date='+60d')
            
            event_data = {
                'name': f"{random.choice(event_types)} #{i+1}",
                'date': start_date,
                'description': fake.text(max_nb_chars=200),
                'capacity': random.randint(10, 50),
                'location': fake.address()[:100],  # Truncate to fit DB
                'mandatory': random.choice([True, False]),
                'leader_id': random.choice(user_ids) if user_ids else 1,
                'points': random.randint(5, 25),
                'created_at': datetime.now(pytz.timezone('US/Eastern'))
            }
            
            events.append(event_data)
        
        self.created_events = events
        return events
    
    def generate_mock_tournaments(self, count=3, user_ids=None):
        """
        Generate mock tournaments for testing
        
        Args:
            count: Number of tournaments to create
            user_ids: List of user IDs for potential participants
            
        Returns:
            list: Created tournament data dictionaries
        """
        tournament_names = [
            "Regional Qualifier", "State Championship", "Invitational Tournament",
            "District Competition", "National Qualifier", "Local Circuit Tournament",
            "Spring Classic", "Fall Invitational", "Winter Championship"
        ]
        
        tournaments = []
        
        for i in range(count):
            tournament_date = fake.date_between(start_date='-60d', end_date='+90d')
            signup_deadline = tournament_date - timedelta(days=random.randint(7, 21))
            
            tournament_data = {
                'name': f"{random.choice(tournament_names)} {fake.year()}",
                'date': tournament_date,
                'signup_deadline': signup_deadline,
                'description': fake.text(max_nb_chars=300),
                'location': f"{fake.city()}, {fake.state_abbr()}",
                'entry_fee': random.choice([0, 25, 50, 75, 100]),
                'max_participants': random.randint(20, 100),
                'created_by': random.choice(user_ids) if user_ids else 1,
                'created_at': datetime.now(pytz.timezone('US/Eastern')),
                'active': True
            }
            
            tournaments.append(tournament_data)
        
        self.created_tournaments = tournaments
        return tournaments
    
    def generate_mock_judges(self, parent_user_ids, child_user_ids):
        """
        Generate mock judge relationships between parents and children
        
        Args:
            parent_user_ids: List of parent user IDs
            child_user_ids: List of child user IDs
            
        Returns:
            list: Judge relationship data
        """
        judges = []
        
        # Create some realistic parent-child judge relationships
        for parent_id in parent_user_ids[:len(child_user_ids)]:
            if child_user_ids:
                child_id = random.choice(child_user_ids)
                child_user_ids.remove(child_id)  # Avoid duplicates
                
                judge_data = {
                    'judge_id': parent_id,
                    'child_id': child_id,
                    'background_check': random.choice([True, False])
                }
                
                judges.append(judge_data)
        
        self.created_judges = judges
        return judges
    
    def generate_mock_tournament_signups(self, tournament_ids, user_ids, signup_rate=0.7):
        """
        Generate realistic tournament signups
        
        Args:
            tournament_ids: List of tournament IDs
            user_ids: List of user IDs
            signup_rate: Percentage of users that sign up for each tournament
            
        Returns:
            list: Tournament signup data
        """
        signups = []
        
        for tournament_id in tournament_ids:
            # Randomly select users to sign up
            participants = random.sample(user_ids, int(len(user_ids) * signup_rate))
            
            for user_id in participants:
                signup_data = {
                    'tournament_id': tournament_id,
                    'user_id': user_id,
                    'signup_date': fake.date_between(start_date='-30d', end_date='today'),
                    'bringing_judge': random.choice([True, False]),
                    'partner_preference': random.choice([None, random.choice(user_ids)]),
                    'dietary_restrictions': random.choice([None, "Vegetarian", "Vegan", "Gluten-free", "None"]),
                    'emergency_contact': fake.phone_number()[:15]
                }
                
                signups.append(signup_data)
        
        return signups
    
    def generate_mock_tournament_results(self, tournament_id, user_ids):
        """
        Generate realistic tournament performance results
        
        Args:
            tournament_id: Tournament ID
            user_ids: List of participating user IDs
            
        Returns:
            list: Tournament performance data
        """
        results = []
        
        # Generate realistic score distribution
        num_participants = len(user_ids)
        random.shuffle(user_ids)  # Randomize rankings
        
        for rank, user_id in enumerate(user_ids, 1):
            # Higher-ranked participants get more points
            base_points = max(0, 100 - rank * 2)
            points = base_points + random.randint(-10, 10)
            
            result_data = {
                'tournament_id': tournament_id,
                'user_id': user_id,
                'rank': rank,
                'points': max(0, points),
                'wins': random.randint(0, 6),
                'losses': random.randint(0, 6),
                'speaker_points': random.uniform(25.0, 30.0),
                'partner_id': None,  # Can be expanded for partner events
                'dropped': random.choice([False, False, False, True])  # 25% drop rate
            }
            
            results.append(result_data)
        
        return results
    
    def generate_complete_mock_scenario(self, num_users=30, num_events=8, num_tournaments=4):
        """
        Generate a complete mock scenario with interconnected data
        """
        print(f"[MOCK DATA] Generating complete scenario: {num_users} users, {num_events} events, {num_tournaments} tournaments")
        
        # Generate users first
        users = self.generate_mock_users(num_users)
        user_ids = [user['id'] for user in users]
        
        # Generate events with user participation
        events = self.generate_mock_events(num_events, user_ids[:num_events*3])  # Some users join multiple events
        event_ids = [event['id'] for event in events]
        
        # Generate tournaments
        tournaments = self.generate_mock_tournaments(num_tournaments, user_ids)
        tournament_ids = [tournament['id'] for tournament in tournaments]
        
        # Generate tournament signups
        signups = self.generate_mock_tournament_signups(tournament_ids, user_ids)
        
        # Generate judges
        parent_users = [u for u in users if u.get('is_parent', False)]
        child_users = [u for u in users if not u.get('is_parent', False)]
        judges = self.generate_mock_judges([u['id'] for u in parent_users], [u['id'] for u in child_users])
        
        # Generate tournament results
        results = []
        for tournament_id in tournament_ids:
            tournament_results = self.generate_mock_tournament_results(tournament_id, user_ids[:15])  # Subset of users
            results.extend(tournament_results)
        
        # Collect all created data
        created_data = {
            'users': users,
            'events': events,
            'tournaments': tournaments,
            'signups': signups,
            'judges': judges,
            'results': results,
            'stats': {
                'total_users': len(users),
                'total_events': len(events),
                'total_tournaments': len(tournaments),
                'total_signups': len(signups),
                'total_judges': len(judges),
                'total_results': len(results)
            }
        }
        
        return created_data
    
    # Convenience wrapper methods
    def generate_users(self, count=10):
        """Wrapper for generate_mock_users for compatibility"""
        return self.generate_mock_users(count)
    
    def generate_events(self, count=5):
        """Wrapper for generate_mock_events for compatibility"""
        return self.generate_mock_events(count)
    
    def generate_tournaments(self, count=3):
        """Wrapper for generate_mock_tournaments for compatibility"""
        return self.generate_mock_tournaments(count)
    
    def generate_judges(self, count=10):
        """Wrapper for generate_mock_judges for compatibility"""
        # Create some mock user IDs for parent and child users
        parent_ids = list(range(1, min(count//2, 5) + 1))
        child_ids = list(range(max(parent_ids) + 1, max(parent_ids) + count - len(parent_ids) + 1))
        return self.generate_mock_judges(parent_ids, child_ids)

def add_required_dependencies():
    """Add required dependencies to requirements.txt if not present"""
    import os
    
    requirements_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'requirements.txt'
    )
    
    new_dependencies = [
        'pytest',
        'pytest-flask', 
        'faker',
        'coverage'
    ]
    
    # Read existing requirements
    existing_requirements = set()
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r') as f:
            existing_requirements = set(line.strip().lower() for line in f if line.strip())
    
    # Add new dependencies if not present
    new_deps_to_add = []
    for dep in new_dependencies:
        if dep.lower() not in existing_requirements:
            new_deps_to_add.append(dep)
    
    if new_deps_to_add:
        with open(requirements_path, 'a') as f:
            f.write('\n' + '\n'.join(new_deps_to_add) + '\n')
        print(f"Added dependencies: {', '.join(new_deps_to_add)}")
    else:
        print("All required testing dependencies already present")

if __name__ == "__main__":
    # Example usage
    generator = MockDataGenerator()
    mock_data = generator.generate_complete_mock_scenario()
    
    print(f"Generated {len(mock_data['users'])} users")
    print(f"Generated {len(mock_data['events'])} events")
    print(f"Generated {len(mock_data['tournaments'])} tournaments")

# Convenience functions for backward compatibility
def generate_mock_users(count=10):
    """Generate mock users (backward compatibility function)"""
    generator = MockDataGenerator()
    return generator.generate_users(count)

def generate_mock_events(count=5):
    """Generate mock events (backward compatibility function)"""
    generator = MockDataGenerator()
    return generator.generate_events(count)

def generate_mock_tournaments(count=3):
    """Generate mock tournaments (backward compatibility function)"""
    generator = MockDataGenerator()
    return generator.generate_tournaments(count)

def generate_mock_judges(count=10):
    """Generate mock judges (backward compatibility function)"""
    generator = MockDataGenerator()
    return generator.generate_judges(count)
    print(f"Generated {len(mock_data['judges'])} judge relationships")