# Mason-SND

---

## My pledge
⚔️⚔️⚔️⚔️⚔️⚔️⚔️⚔️⚔️

For too long AI has drained the soul of programming. Those who enjoy coding were paralyzed by a mahcine that made them dumber. I am a victim of this silent crime. But, I am back with my spine this time. This code base will no longer use AI to do the hard work for me. This is a war on AI slop, may it never fester in my projects gain!


Here is my 3 step plan to removing it from my codebase:
1. Reread all my files and create my own comments for understanding
2. Stop adding features using AI
3. When I need to add a feature, reprogram all the code in that section myself if it was slop coded.

This way I can make changes everywhere and consistently.

⚔️⚔️⚔️⚔️⚔️⚔️⚔️⚔️⚔️

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [File Structure](#file-structure)
4. [Application Architecture](#application-architecture)
5. [Blueprints & Routing](#blueprints--routing)
6. [Database Models](#database-models)
7. [Templates & Frontend](#templates--frontend)
8. [Testing System](#testing-system)
9. [Configuration & Environment](#configuration--environment)
10. [Common Workflows and Naming](#common-workflows-and-naming)

---

## Project Overview

**Mason-SND** is a website that makes it easier to track competitor performance, create rosters, sign up forms, and manage members and judges. The application provides:

- **User Management:** Student accounts, parent/judge accounts with role-based access control
- **Tournament Management:** Create tournaments, handle signups, manage judges, submit and track results
- **Event Management:** Create events, manage event members, and give effort points.
- **Metrics & Analytics:** Track student performance, rankings, points, and trends
- **Roster Generation:** Automated tournament roster creation with judge pairing and opportunities for newer members as well as seasoned members.
- **Requirements Tracking:** Automated requirement assignment and deadline management
- **Testing Suite:** Cooked testing and simulation infrastructure that I vibe coded (WILL FIX)

### Key Features

- Multi-role system (Student, Event Leader, Admin/Chair)
- Parent-child account relationships for judges
- Tournament signup with custom forms
- Partner event support for team competitions
- Points and ranking calculations with configurable weights
- Roster publishing with penalty entry tracking
- Race condition protection on critical operations
- Automated ghost account creation for unregistered parents/students

---

## Technology Stack

### Backend
- **Framework:** Flask
- **Database:** SQLite with SQLAlchemy ORM
- **Migrations:** Flask-Migrate (Alembic)
- **Security:** Flask-WTF (CSRF protection), Werkzeug (password hashing)
- **Timezone:** pytz (Eastern Time zone handling)

### Frontend
- **Templating:** Jinja2
- **Static Files:** CSS, JavaScript (in `mason_snd/static/`)

### Testing & Development
- **Testing Framework:** pytest, pytest-flask
- **Mock Data:** Faker library
- **Code Coverage:** coverage.py
- **Data Export:** pandas, openpyxl (Excel exports)

### Deployment
- **Environment:** Tmux container in Ubunut Server
- **Configuration:** python-dotenv for environment variables

---

### Directory Roles

- **`mason_snd/`**: Core application code
- **`mason_snd/blueprints/`**: Modular route handlers organized by feature
- **`mason_snd/models/`**: Database schema definitions using SQLAlchemy
- **`mason_snd/templates/`**: HTML templates with Jinja2 syntax
- **`mason_snd/static/`**: CSS, JavaScript, images, and other static files
- **`UNIT_TEST/`**: Isolated testing infrastructure (see Testing System section)
- **`migrations/`**: Database schema version control
- **`instance/`**: Runtime data (databases, uploads) - gitignored

---

## Application Architecture

### App Factory Pattern

The application uses the factory pattern defined in `mason_snd/__init__.py`:

```python
def create_app():
    app = Flask(__name__)
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default-secret')
    
    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    Migrate(app, db)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    # ... more blueprints
    
    # Testing integration (if ENABLE_TESTING=True) chopped and doesnt work well
    if os.getenv('ENABLE_TESTING'):
        from UNIT_TEST.integration import integrate_testing_with_app
        integrate_testing_with_app(app)
    
    return app
```

### Extensions

Defined in `mason_snd/extensions.py`:
- **`db`**: SQLAlchemy database instance
- **`csrf`**: CSRFProtect instance for form security

### Role-Based Access Control

Users have a `role` field:
- **0 = Member (Student)**: Basic access, can view own profile and join events
- **1 = Event Leader (EL)**: Can manage specific events and their members
- **2 = Chair/Admin**: Full administrative access

### Parent-Child Relationships

The system supports **judge (parent)** and **child (student)** relationships via the `Judges` model, enabling:
- Parents to view their child's profile and requirements
- Children to request judges for tournaments
- Automated requirement generation for both roles

---

## Blueprints & Routing

Each blueprint handles a specific domain of the application.

### 1. **Auth Blueprint** (`/auth`)

**File:** `mason_snd/blueprints/auth/auth.py`

**Purpose:** Authentication, user registration, and automated requirement generation.

#### Routes

| Route | Methods | Function | Description |
|-------|---------|----------|-------------|
| `/auth/login` | GET, POST | `login()` | User login form and authentication |
| `/auth/logout` | GET | `logout()` | Clear session and redirect to login |
| `/auth/register` | GET, POST | `register()` | New user registration with role selection |

#### Key Functions

- **`make_all_requirements()`**: Creates standard requirements in the database
- **`make_child_reqs(user)`**: Assigns requirements for student users
- **`make_judge_reqs(user)`**: Assigns requirements for parent/judge users
- **`req_checks(user)`**: Updates requirement completion status dynamically
- **`find_or_create_user()`**: Handles ghost account claiming during registration
- **`create_or_update_judge_relationship()`**: Manages parent-child links

#### Special Features

- **Ghost Account Creation**: When a student registers, a ghost account is created for their emergency contact (parent). When the parent registers, they claim this ghost account.
- **Automatic Requirement Assignment**: Requirements are assigned based on user role and current status (e.g., "Submit Tournament Performance" only if they attended but didn't submit).
- **Race Condition Protection**: Registration uses `@prevent_race_condition` decorator to prevent duplicate submissions.

---

### 2. **Profile Blueprint** (`/profile`)

**File:** `mason_snd/blueprints/profile/profile.py`

**Purpose:** User profile viewing and editing.

#### Routes

| Route | Methods | Function | Description |
|-------|---------|----------|-------------|
| `/profile/user/<user_id>` | GET | `index(user_id)` | View user profile with requirements and notifications |
| `/profile/update` | GET, POST | `update()` | Edit current user's profile information |
| `/profile/add_judge` | GET, POST | `add_judge()` | Add a judge (parent) to your account |
| `/profile/add_child` | GET, POST | `add_child()` | Add a child to your judge account |
| `/profile/dismiss_popup/<popup_id>` | POST | `dismiss_popup(popup_id)` | Mark admin popup notification as completed |

#### Key Features

- **Access Control**: Users can only view their own profile unless they're an admin or have a parent-child relationship
- **Roster Notifications**: Users see when they've been assigned to a published roster
- **Popup Messages**: Admins can send targeted messages with optional expiration
- **Ghost Account Creation**: Updating emergency contact or child information creates ghost accounts if they don't exist

---

### 3. **Events Blueprint** (`/events`)

**File:** `mason_snd/blueprints/events/events.py`

**Purpose:** Manage competitive events (Speech, LD, PF).

#### Routes

| Route | Methods | Function | Description |
|-------|---------|----------|-------------|
| `/events/` | GET | `index()` | List all events |
| `/events/add_event` | GET, POST | `add_event()` | Create a new event (admin only) |
| `/events/edit_event/<event_id>` | GET, POST | `edit_event(event_id)` | Edit event details |
| `/events/delete_event/<event_id>` | POST | `delete_event(event_id)` | Delete an event |
| `/events/join_event/<event_id>` | POST | `join_event(event_id)` | Student joins an event |
| `/events/leave_event/<event_id>` | POST | `leave_event(event_id)` | Student leaves an event |
| `/events/manage_members/<event_id>` | GET, POST | `manage_members(event_id)` | Event leader manages members and effort scores |
| `/events/download_event_members/<event_id>` | GET | `download_event_members(event_id)` | Export event members to CSV |
| `/events/download_all_events_stats` | GET | `download_all_events_stats()` | Export all events data to CSV |

#### Key Features

- **Event Types**: 0 = Speech, 1 = LD, 2 = PF
- **Partner Events**: Can be flagged as requiring partners (for PF)
- **Multiple Event Leaders**: Uses `Event_Leader` model for multiple leaders per event
- **Effort Scores**: Event leaders can assign effort points to students
- **Emoji Support**: Each event has an emoji for fun

---

### 4. **Tournaments Blueprint** (`/tournaments`)

**File:** `mason_snd/blueprints/tournaments/tournaments.py`

**Purpose:** Tournament creation, signups, judge management, and results submission.

#### Routes

| Route | Methods | Function | Description |
|-------|---------|----------|-------------|
| `/tournaments/` | GET | `index()` | List upcoming tournaments |
| `/tournaments/add_tournament` | GET, POST | `add_tournament()` | Create new tournament (admin) |
| `/tournaments/add_form` | GET, POST | `add_form()` | Add custom form fields to tournament |
| `/tournaments/signup` | GET, POST | `signup()` | Student signs up for tournament and event |
| `/tournaments/bringing_judge/<tournament_id>` | GET, POST | `bringing_judge(tournament_id)` | Request parent to judge |
| `/tournaments/judge_requests` | GET, POST | `judge_requests()` | Parents view/accept judge requests |
| `/tournaments/my_tournaments` | GET | `my_tournaments()` | View user's tournament signups |
| `/tournaments/submit_results/<tournament_id>` | GET, POST | `submit_results(tournament_id)` | Students submit their performance |
| `/tournaments/view_results/<tournament_id>` | GET | `view_results(tournament_id)` | View submitted results |
| `/tournaments/tournament_results/<tournament_id>` | GET, POST | `tournament_results(tournament_id)` | Admin edits all results |
| `/tournaments/delete_tournament/<tournament_id>` | POST | `delete_tournament(tournament_id)` | Delete tournament |
| `/tournaments/search_partners` | GET | `search_partners()` | Find tournament partners for partner events |

#### Key Features

- **Custom Forms**: Tournaments can have dynamic form fields for additional data collection
- **Judge Requests**: Students can request their parent to judge, tracked in `Tournament_Judges`
- **Partner Matching**: For partner events, students can search and pair up
- **Performance Tracking**: Rank, stage (octas, quarters, etc.), points, and bid status
- **Results Submission Lock**: Once admin marks `results_submitted=True`, students can't edit
- **Issue**: Currently can't edit or delete forms and signups.

---

### 5. **Rosters Blueprint** (`/rosters`)

**File:** `mason_snd/blueprints/rosters/rosters.py`

**Purpose:** Generate tournament rosters with judge pairing and competitor assignment.

#### Routes

| Route | Methods | Function | Description |
|-------|---------|----------|-------------|
| `/rosters/` | GET | `index()` | List all rosters |
| `/rosters/view_tournament/<tournament_id>` | GET | `view_tournament(tournament_id)` | View roster for a tournament |
| `/rosters/save_roster/<tournament_id>` | POST | `save_roster(tournament_id)` | Generate/update roster for tournament |
| `/rosters/publish_roster/<roster_id>` | POST | `publish_roster(roster_id)` | Publish roster (notify users) |
| `/rosters/unpublish_roster/<roster_id>` | POST | `unpublish_roster(roster_id)` | Unpublish roster |
| `/rosters/view_roster/<roster_id>` | GET | `view_roster(roster_id)` | View specific roster details |
| `/rosters/download_roster/<roster_id>` | GET | `download_roster(roster_id)` | Download roster as CSV |
| `/rosters/download_tournament/<tournament_id>` | GET | `download_tournament(tournament_id)` | Download tournament roster as CSV |
| `/rosters/rename_roster/<roster_id>` | GET, POST | `rename_roster(roster_id)` | Rename a roster |
| `/rosters/delete_roster/<roster_id>` | POST | `delete_roster(roster_id)` | Delete a roster |
| `/rosters/upload_roster` | GET, POST | `upload_roster()` | Upload roster from CSV |

#### Key Features

- **Automated Pairing**: Matches competitors with judges based on availability
- **Points-Based Ranking**: Sorts competitors by total points (tournament + effort)
- **Penalty Entries**: Tracks "+1" penalty spots in rosters
- **Publishing System**: Notifies users when roster is published via `User_Published_Rosters`
- **Partner Support**: Handles partner events with `Roster_Partners` model

---

### 6. **Metrics Blueprint** (`/metrics`)

**File:** `mason_snd/blueprints/metrics/metrics.py`

**Purpose:** Analytics, performance tracking, rankings, and data exports.

#### Routes

| Route | Methods | Function | Description |
|-------|---------|----------|-------------|
| `/metrics/` | GET | `index()` | Metrics dashboard home |
| `/metrics/user_metrics` | GET | `user_metrics()` | View all users with points/rankings |
| `/metrics/user_metrics/download` | GET | `download()` | Export user metrics to CSV |
| `/metrics/user/<user_id>` | GET | `user(user_id)` | Individual user performance details |
| `/metrics/event/<event_id>` | GET | `event(event_id)` | Event-specific metrics |
| `/metrics/events` | GET | `events()` | All events overview |
| `/metrics/download_events` | GET | `download_events()` | Export events data |
| `/metrics/tournament/<tournament_id>` | GET | `tournament(tournament_id)` | Tournament-specific metrics |
| `/metrics/tournaments` | GET | `tournaments()` | All tournaments overview |
| `/metrics/download_tournaments` | GET | `download_tournaments()` | Export tournaments data |
| `/metrics/my_metrics` | GET | `my_metrics()` | Current user's performance summary |
| `/metrics/my_performance_trends` | GET | `my_performance_trends()` | User's performance over time |
| `/metrics/my_ranking` | GET | `my_ranking()` | User's ranking among peers |
| `/metrics/settings` | GET, POST | `settings()` | Configure metrics weights (admin) |

#### Key Features

- **Weighted Points**: Configurable weights for tournament points vs. effort points
- **Ranking System**: Automatically ranks users based on total points
- **Performance Trends**: Tracks performance over time
- **CSV/Excel Exports**: All data can be exported for external analysis
- **Pagination**: Large datasets are paginated for performance

#### Helper Functions

- **`get_point_weights()`**: Returns current effort/tournament weight configuration
- **`normalize_timestamp_for_comparison(timestamp)`**: Handles timezone-aware comparisons

---

### 7. **Admin Blueprint** (`/admin`)

**File:** `mason_snd/blueprints/admin/admin.py`

**Purpose:** Administrative functions for managing users, events, tournaments, requirements, and testing.



| Route | Methods | Function | Description |
|-------|---------|----------|-------------|
| `/admin/` | GET | `index()` | Admin dashboard home |
| `/admin/requirements` | GET, POST | `requirements()` | Manage requirements and assignments |
| `/admin/add_popup` | GET, POST | `add_popup()` | Send popup messages to users |
| `/admin/user/<user_id>` | GET, POST | `user(user_id)` | Edit user details |
| `/admin/search` | GET, POST | `search()` | Search for users |
| `/admin/add_drop/<user_id>` | POST | `add_drop(user_id)` | Add drop to user account |
| `/admin/events_management` | GET | `events_management()` | Manage all events |
| `/admin/change_event_leader/<event_id>` | GET, POST | `change_event_leader(event_id)` | Reassign event leader |
| `/admin/test_data` | GET, POST | `test_data()` | Generate test users/tournaments |
| `/admin/delete_management` | GET | `delete_management()` | Deletion dashboard |
| `/admin/delete_users` | GET, POST | `delete_users()` | Bulk delete users safely |
| `/admin/delete_tournaments` | GET, POST | `delete_tournaments()` | Bulk delete tournaments |
| `/admin/delete_events` | GET, POST | `delete_events()` | Bulk delete events |
| `/admin/delete_requirements` | GET, POST | `delete_requirements()` | Bulk delete requirements |
| `/admin/view_tournament_signups/<tournament_id>` | GET | `view_tournament_signups(tournament_id)` | View all signups for tournament |
| `/admin/download_tournament_signups/<tournament_id>` | GET | `download_tournament_signups(tournament_id)` | Export signups to Excel |
| `/admin/download_all_signups` | GET | `download_all_signups()` | Export all signups to Excel |
| `/admin/testing_suite` | GET | `testing_suite()` | Access testing dashboard |
| `/admin/testing/*` | Various | Multiple testing routes | Testing system integration (20+ routes) |

#### Key Features

- **Safe Deletion**: Uses `deletion_utils.py` for cascade-aware deletion with preview
- **Bulk Operations**: Can delete/modify multiple items at once
- **User Search**: Smart search with fuzzy matching
- **Excel Exports**: Tournament signups exported with pandas/openpyxl
- **Testing Integration**: Direct access to testing suite from admin panel
- **Popup System**: Send time-limited messages to specific users
- **Issue**: A five year old could organize this admin panel better. I'll fix it.

---

### 8. **Main Blueprint** (`/`)

**File:** `mason_snd/blueprints/main/main.py`

**Purpose:** Home page, SEO files, and general routes.

#### Routes

| Route | Methods | Function | Description |
|-------|---------|----------|-------------|
| `/` | GET | `index()` | Application home page |
| `/life` | GET | `life()` | Easter egg / test page |
| `/favicon.ico`, `/favicon` | GET | `favicon()` | Serve favicon |
| `/sitemap.xml` | GET | `sitemap()` | Generate XML sitemap |
| `/robots.txt` | GET | `robots()` | Generate robots.txt |

---

## Database Models

All models use SQLAlchemy ORM and are located in `mason_snd/models/`.

### **User Model** (`auth.py`)

**Table:** `user`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `first_name` | String(50) | User's first name (stored lowercase) |
| `last_name` | String(50) | User's last name (stored lowercase) |
| `email` | String(50) | Email address |
| `password` | String(500) | Hashed password |
| `phone_number` | String(50) | Phone number |
| `is_parent` | Boolean | True if parent/judge, False if student |
| `role` | Integer | 0=Member, 1=Event Leader, 2=Admin |
| `account_claimed` | Boolean | False for ghost accounts |
| `points` | Integer | Total calculated points |
| `drops` | Integer | Number of penalty drops |
| `bids` | Integer | Total bids earned |
| `tournaments_attended_number` | Integer | Count of tournaments attended |
| `emergency_contact_*` | String | Emergency contact info (for students) |
| `child_first_name`, `child_last_name` | String | Child info (for parents) |
| `judging_reqs` | String(5000) | Judge-specific requirements |

**Properties:**
- `tournament_points`: Calculated from `Tournament_Performance`
- `effort_points`: Calculated from `Effort_Score`

**Relationships:**
- `published_rosters` → `User_Published_Rosters`
- `penalty_entries` → `Roster_Penalty_Entries`
- `judge`, `child` → `Judges` (via foreign keys)
- Many relationships to tournaments, events, requirements, etc.

---

### **Judges Model** (`auth.py`)

**Table:** `judges`

Links parents to children for judging relationships.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `background_check` | Boolean | Background check status |
| `judge_id` | Integer | FK to User (parent) |
| `child_id` | Integer | FK to User (student) |

---

### **User_Published_Rosters Model** (`auth.py`)

**Table:** `user_published_rosters`

Tracks when a user is included in a published roster.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `user_id` | Integer | FK to User |
| `roster_id` | Integer | FK to Roster |
| `tournament_id` | Integer | FK to Tournament |
| `event_id` | Integer | FK to Event |
| `notified` | Boolean | Whether user has seen notification |
| `created_at` | DateTime | When roster was published |

---

### **Roster_Penalty_Entries Model** (`auth.py`)

**Table:** `roster_penalty_entries`

Tracks "+1" penalty entries in rosters (for students with drops).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `roster_id` | Integer | FK to Roster |
| `tournament_id` | Integer | FK to Tournament |
| `event_id` | Integer | FK to Event |
| `penalized_user_id` | Integer | FK to User |
| `original_rank` | Integer | Original ranking position |
| `drops_applied` | Integer | Number of drops applied |
| `created_at` | DateTime | Timestamp |

---

### **Tournament Model** (`tournaments.py`)

**Table:** `tournament`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `name` | String(255) | Tournament name |
| `date` | DateTime | Tournament date |
| `address` | String(255) | Tournament location |
| `signup_deadline` | DateTime | Signup cutoff |
| `performance_deadline` | DateTime | Results submission cutoff |
| `results_submitted` | Boolean | Admin has finalized results |
| `created_at` | DateTime | Creation timestamp |

**Relationships:**
- `form_fields` → `Form_Fields`
- `form_responses` → `Form_Responses`
- `tournament_signups` → `Tournament_Signups`
- `tournament_performances` → `Tournament_Performance`
- `tournament_judges` → `Tournament_Judges`
- `tournament_partners` → `Tournament_Partners`
- `rosters` → `Roster`

---

### **Form_Fields Model** (`tournaments.py`)

**Table:** `form_fields`

Custom form fields for tournament signups.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `label` | Text | Field label/question |
| `type` | Text | Field type (text, checkbox, dropdown, etc.) |
| `options` | Text | Options for dropdown/radio (JSON/comma-separated) |
| `required` | Boolean | Whether field is required |
| `tournament_id` | Integer | FK to Tournament |

---

### **Form_Responses Model** (`tournaments.py`)

**Table:** `form_responses`

User responses to custom form fields.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `response` | Text | User's answer |
| `submitted_at` | DateTime | Submission timestamp |
| `tournament_id` | Integer | FK to Tournament |
| `user_id` | Integer | FK to User |
| `field_id` | Integer | FK to Form_Fields |

---

### **Tournament_Signups Model** (`tournaments.py`)

**Table:** `tournament_signups`

User signups for tournaments.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `bringing_judge` | Boolean | User is bringing a judge |
| `is_going` | Boolean | Confirmed attendance |
| `user_id` | Integer | FK to User (student) |
| `tournament_id` | Integer | FK to Tournament |
| `event_id` | Integer | FK to Event |
| `judge_id` | Integer | FK to User (judge being brought) |
| `partner_id` | Integer | FK to User (partner for partner events) |

---

### **Tournament_Performance Model** (`tournaments.py`)

**Table:** `tournament_performance`

Student performance results at tournaments.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `points` | Integer | Points earned |
| `bid` | Boolean | Earned a bid |
| `rank` | Integer | Final ranking |
| `stage` | Integer | 0=None, 1=Double Octas, 2=Octas, 3=Quarters, 4=Semis, 5=Finals |
| `user_id` | Integer | FK to User |
| `tournament_id` | Integer | FK to Tournament |

---

### **Tournament_Judges Model** (`tournaments.py`)

**Table:** `tournament_judges`

Judge requests and acceptances for tournaments.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `accepted` | Boolean | Judge accepted request |
| `judge_id` | Integer | FK to User (parent/judge) |
| `child_id` | Integer | FK to User (student) |
| `tournament_id` | Integer | FK to Tournament |
| `event_id` | Integer | FK to Event |

---

### **Tournament_Partners Model** (`tournaments.py`)

**Table:** `tournament_partners`

Partner pairing for partner events.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `partner1_user_id` | Integer | FK to User |
| `partner2_user_id` | Integer | FK to User |
| `tournament_id` | Integer | FK to Tournament |
| `event_id` | Integer | FK to Event |
| `created_at` | DateTime | Pairing timestamp |

---

### **Tournaments_Attended Model** (`tournaments.py`)

**Table:** `tournaments_attended`

Simple tracking of tournament attendance.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `user_id` | Integer | FK to User |
| `tournament_id` | Integer | FK to Tournament |

---

### **Event Model** (`events.py`)

**Table:** `event`

Competitive events (Speech, LD, PF).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `event_name` | String | Event name |
| `event_description` | String | Description |
| `event_emoji` | String | Emoji for display |
| `owner_id` | Integer | FK to User (creator) |
| `event_type` | Integer | 0=Speech, 1=LD, 2=PF |
| `is_partner_event` | Boolean | Requires partners |

**Relationships:**
- `leaders` → `Event_Leader` (many-to-many for multiple leaders)
- `user_event` → `User_Event`

**Properties:**
- `leader_users`: Returns list of all leader User objects

---

### **Event_Leader Model** (`events.py`)

**Table:** `event_leader`

Multiple event leaders per event.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `event_id` | Integer | FK to Event |
| `user_id` | Integer | FK to User |

---

### **User_Event Model** (`events.py`)

**Table:** `user_event`

Student membership in events.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `effort_score` | Integer | Current effort score |
| `active` | Boolean | Active membership |
| `event_id` | Integer | FK to Event |
| `user_id` | Integer | FK to User |

---

### **Effort_Score Model** (`events.py`)

**Table:** `effort_score`

Effort points awarded to students by event leaders.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `score` | Integer | Points awarded |
| `timestamp` | DateTime | When awarded (EST) |
| `user_id` | Integer | FK to User (recipient) |
| `event_id` | Integer | FK to Event |
| `given_by_id` | Integer | FK to User (event leader) |

---

### **Roster Model** (`rosters.py`)

**Table:** `roster`

Tournament rosters.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `name` | String | Roster name |
| `published` | Boolean | Roster is published |
| `published_at` | DateTime | Publication timestamp |
| `tournament_id` | Integer | FK to Tournament |
| `date_made` | DateTime | Creation timestamp |

**Relationships:**
- `roster_judge_roster` → `Roster_Judge`
- `roster_judge_roster_competitors` → `Roster_Competitors`
- `roster_partners` → `Roster_Partners`

---

### **Roster_Judge Model** (`rosters.py`)

**Table:** `roster_judge`

Judges assigned to rosters.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `user_id` | Integer | FK to User (judge) |
| `child_id` | Integer | FK to User (child) |
| `event_id` | Integer | FK to Event |
| `roster_id` | Integer | FK to Roster |
| `people_bringing` | Integer | Number of competitors this judge covers |

---

### **Roster_Competitors Model** (`rosters.py`)

**Table:** `roster_competitors`

Competitors assigned to rosters.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `user_id` | Integer | FK to User (competitor) |
| `event_id` | Integer | FK to Event |
| `judge_id` | Integer | FK to User (assigned judge) |
| `roster_id` | Integer | FK to Roster |

---

### **Roster_Partners Model** (`rosters.py`)

**Table:** `roster_partners`

Partner pairs in rosters.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `partner1_user_id` | Integer | FK to User |
| `partner2_user_id` | Integer | FK to User |
| `roster_id` | Integer | FK to Roster |

---

### **User_Requirements Model** (`admin.py`)

**Table:** `user_requirements`

User-specific requirement assignments.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `complete` | Boolean | Requirement completed |
| `deadline` | DateTime | Deadline (EST) |
| `user_id` | Integer | FK to User |
| `requirement_id` | Integer | FK to Requirements |

---

### **Requirements Model** (`admin.py`)

**Table:** `requirements`

Template requirements.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `body` | String | Requirement description |
| `active` | Boolean | Currently active |

**Standard Requirements:**
1. Submit Final Forms
2. Pay Membership Fee on PaySchools
3. Submit Tournament Performance
4. Join an Event
5. Sign the Permission slip for GMV tournaments
6. Pay your Tournament Fees
7. Complete background check (judges)
8. Respond to Judging Request by Child (judges)
9. Complete your judge training (judges)

---

### **Popups Model** (`admin.py`)

**Table:** `popups`

Admin messages to users.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `message` | Text | Message content |
| `created_at` | DateTime | Creation time (EST) |
| `expires_at` | DateTime | Optional expiration |
| `completed` | Boolean | User dismissed |
| `user_id` | Integer | FK to User (recipient) |
| `admin_id` | Integer | FK to User (sender) |

---

### **MetricsSettings Model** (`metrics.py`)

**Table:** `metrics_settings`

Configurable point weights.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `effort_weight` | Float | Weight for effort points (default 0.3) |
| `tournament_weight` | Float | Weight for tournament points (default 0.7) |

**Usage:**
```python
Total Points = (effort_points * effort_weight) + (tournament_points * tournament_weight)
```

---

## Templates & Frontend

### Template Organization

Templates are organized by blueprint in `mason_snd/templates/`:

- **`admin/`**: Admin panel interfaces
- **`auth/`**: Login/registration forms
- **`events/`**: Event management pages
- **`tournaments/`**: Tournament pages
- **`metrics/`**: Analytics dashboards
- **`rosters/`**: Roster displays
- **`profile/`**: User profile pages
- **`main/`**: Home and general pages
- **`partials/`**: Reusable components (headers, footers, modals)
- **`errors/`**: Error pages (404, 403, 500)

### Base Template Pattern

Most templates extend a base template (e.g., `admin/base.html`, `main/base.html`) using Jinja2 inheritance:

```jinja2
{% extends 'admin/base.html' %}

{% block title %}Page Title{% endblock %}

{% block content %}
  <!-- Page-specific content -->
{% endblock %}
```

### Common Template Features

- **Flash Messages**: Displayed via `{% with messages = get_flashed_messages() %}`
- **User Context**: Current user available via `session['user_id']`
- **CSRF Protection**: All forms include `{{ csrf_token() }}` or `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`
- **Dynamic Navigation**: Menu items change based on user role

### Key Templates

- **`auth/login.html`**: Login form
- **`auth/register.html`**: Registration with conditional parent/student fields
- **`profile/profile.html`**: User profile with requirements, popups, and roster notifications
- **`tournaments/index.html`**: Tournament listing
- **`tournaments/signup.html`**: Tournament signup with custom forms
- **`rosters/view_tournament.html`**: Tournament roster display
- **`metrics/user_metrics.html`**: User rankings table
- **`admin/index.html`**: Admin dashboard

---

## Testing System

The `UNIT_TEST/` directory contains a comprehensive testing infrastructure **strictly isolated from production data**.

### Key Principles
This "testing system" is AI Slop and will be purged.

- **Production Safety First**: All tests run on isolated database copies  
- **Safety Guards**: Automatic verification prevents production data modification  
- **Emergency Cleanup**: Tools to remove all test artifacts  
- **Web Dashboard**: Browser-based testing interface  

### Testing Components

#### 1. **Master Controller** (`master_controller.py`)

Central orchestration for test suites.

**Usage:**
```bash
# Quick test suite (fast, essential tests)
python UNIT_TEST/master_controller.py --quick

# Full test suite (comprehensive)
python UNIT_TEST/master_controller.py --full
```

#### 2. **Production Safety** (`production_safety.py`)

Guards against accidental production data modification.

**Usage:**
```bash
# Check safety status
python UNIT_TEST/production_safety.py --check

# Emergency cleanup
python UNIT_TEST/production_safety.py --cleanup
```

#### 3. **Final Verification** (`final_verification.py`)

Pre-deployment verification suite.

**Usage:**
```bash
# Verify system before deployment
python UNIT_TEST/final_verification.py --verify

# Generate verification report
python UNIT_TEST/final_verification.py --verify --report
```

#### 4. **Web Dashboard** (`web_dashboard/dashboard.py`)

Browser-based testing interface.

**Access:**
1. Set `ENABLE_TESTING=True` in environment
2. Start Flask: `flask run`
3. Navigate to `/test_dashboard`

**Features:**
- Run quick/full tests
- View test results
- Database snapshots
- Cleanup operations

#### 5. **Integration** (`integration.py`)

Integrates testing system with main Flask app.

**Function:**
```python
from UNIT_TEST.integration import integrate_testing_with_app

if app.config.get('ENABLE_TESTING'):
    integrate_testing_with_app(app)
```

**Adds:**
- CLI commands: `flask run_tests`, `flask verify_tests`, `flask cleanup_tests`
- Testing routes under `/test_dashboard`
- Template context with testing status

#### 6. **Mock Data Generators** (`mock_data/`)

Generate realistic test data.

- **`generators.py`**: User, tournament, event generators
- **`tournament_simulator.py`**: Simulate complete tournament workflows

### Environment Variables for Testing

```bash
ENABLE_TESTING=True       # Enable testing integration
TEST_DB_PATH=/path/to/test.db  # Custom test database location
TEST_DEBUG=True           # Verbose test output
```

### Testing Workflow Example

```bash
# 1. Enable testing
export ENABLE_TESTING=True

# 2. Run quick tests
python UNIT_TEST/master_controller.py --quick

# 3. Verify system
python UNIT_TEST/final_verification.py --verify

# 4. Cleanup test data
python UNIT_TEST/production_safety.py --cleanup
```

---

## Configuration & Environment

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=sqlite:///db.sqlite3

# Security
FLASK_SECRET_KEY=your-secret-key-here

# Flask Environment
FLASK_APP=mason_snd:create_app
FLASK_ENV=production  # or development

# Testing (optional)
ENABLE_TESTING=False
TEST_DB_PATH=/tmp/test_db.sqlite3
```

### `.flaskenv` Configuration

Located at project root:

```bash
FLASK_APP=mason_snd:create_app
FLASK_ENV=production
```

### App Configuration

Set in `mason_snd/__init__.py`:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default-secret')
```

### Running the Application

```bash
# Development
flask run

# With testing enabled
ENABLE_TESTING=True flask run

# Production (use production server like gunicorn)
gunicorn -w 4 -b 0.0.0.0:8000 "mason_snd:create_app()"
```

### Database Migrations

```bash
# Initialize migrations (first time)
flask db init

# Create a migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

---

## Common Workflows and Naming

#### 1. **User Registration Flow**

1. User visits `/auth/register`
2. Selects "Student" or "Parent"
3. Fills in information:
   - **Student**: Personal info + emergency contact (creates ghost parent account)
   - **Parent**: Personal info + child name (creates ghost child account)
4. System checks for existing ghost account with same name
5. If exists and unclaimed: Claims account, updates with new info
6. If exists and claimed: Shows error (or updates missing fields)
7. Creates `Judges` relationship between parent and child
8. Assigns initial requirements based on role
9. Redirects to profile page

#### 2. **Tournament Signup Flow**

1. Student navigates to `/tournaments/signup`
2. Selects tournament, event, and optionally a partner (for partner events)
3. Fills out custom form fields (if tournament has them)
4. Indicates if bringing a judge
5. If bringing judge:
   - Request sent to parent via `Tournament_Judges` (accepted=False)
   - Requirement "Respond to Judging Request" added to parent
6. `Tournament_Signups` record created
7. System checks requirements (e.g., "Join an Event")
8. Confirmation shown

#### 3. **Roster Generation Flow**

1. Admin navigates to `/rosters/view_tournament/<tournament_id>`
2. Clicks "Generate Roster" for an event
3. System:
   - Fetches all signups for tournament + event
   - Calculates total points (tournament + effort) for each student
   - Sorts students by points (descending)
   - Identifies students with drops (adds penalty entries)
   - Matches students with available judges
   - Creates `Roster`, `Roster_Competitors`, `Roster_Judge` records
   - For partner events: Creates `Roster_Partners` records
4. Roster displayed for review
5. Admin can publish roster:
   - Sets `published=True`, `published_at=now()`
   - Creates `User_Published_Rosters` entries for all students
   - Students see notification on profile page

#### 4. **Performance Submission Flow**

1. Student attends tournament (marked in `Tournaments_Attended`)
2. After tournament, requirement "Submit Tournament Performance" appears
3. Student navigates to `/tournaments/submit_results/<tournament_id>`
4. Fills in: Rank, Stage (e.g., "Quarters"), Points, Bid (Yes/No)
5. `Tournament_Performance` record created
6. Requirement automatically removed via `req_checks()`
7. Points updated in metrics

#### 5. **Admin Deletion Flow**

1. Admin navigates to `/admin/delete_management`
2. Chooses entity type (Users, Tournaments, Events, Requirements)
3. Selects items to delete
4. System generates preview showing:
   - All cascading deletions
   - Affected records in related tables
5. Admin confirms
6. `deletion_utils.py` performs safe cascade deletion
7. Success message shown

### Naming conventions

The home page method of a blueprint should always be named 'index()'. The route should always be named '/'

For routes that add, delete, manage, or edit anything, you name them 'action_index_name.' Example: /mange_events, /add_roster, /delete_tournament

---

## Tips for Developers

### Understanding Ghost Accounts

**Ghost accounts** are placeholder accounts created when:
- A student registers and provides their parent's contact info
- A parent registers and provides their child's name

**Characteristics:**
- `account_claimed = False`
- Minimal information (name, phone/email)
- Can be "claimed" when the real person registers
- Prevents orphaned relationships

### Race Condition Protection

The `@prevent_race_condition` decorator prevents duplicate submissions:

```python
@tournaments_bp.route('/signup', methods=['POST'])
@prevent_race_condition('tournament_signup', min_interval=2.0, ...)
def signup():
    # Protected against double-submission
    ...
```

**How it works:**
- Tracks recent submissions by user + operation type
- Blocks duplicate requests within `min_interval` seconds
- Redirects duplicate requests safely

### Timezone Handling

All timestamps use **US/Eastern timezone** (EST):

```python
import pytz
EST = pytz.timezone('US/Eastern')

now = datetime.now(EST)
```

Always use timezone-aware datetimes for consistency.

### Debugging Database Issues

```bash
# Access SQLite database
sqlite3 instance/db.sqlite3

# List tables
.tables

# Describe table
.schema user

# Query
SELECT * FROM user WHERE role = 2;

# Exit
.quit
```

### Adding a New Route

1. Choose the appropriate blueprint (or create new one)
2. Define route function with decorator:
   ```python
   @blueprint_bp.route('/my_route', methods=['GET', 'POST'])
   def my_function():
       # Check authentication
       user_id = session.get('user_id')
       if not user_id:
           return redirect(url_for('auth.login'))
       
       # Your logic here
       return render_template('blueprint/my_template.html')
   ```
3. Create template in `templates/blueprint/my_template.html`
4. Test route
5. Update this documentation

### Adding a New Model

1. Create/edit model file in `mason_snd/models/`
2. Define model class:
   ```python
   class MyModel(db.Model):
       id = db.Column(db.Integer, primary_key=True)
       # ... columns
   ```
3. Generate migration:
   ```bash
   flask db migrate -m "Add MyModel"
   ```
4. Review migration in `migrations/versions/`
5. Apply migration:
   ```bash
   flask db upgrade
   ```
6. Update this documentation

---

## Appendix: Quick Reference

### User Roles
- **0**: Member (Student)
- **1**: Event Leader
- **2**: Admin/Chair

### Event Types
- **0**: Speech
- **1**: LD (Lincoln-Douglas)
- **2**: PF (Public Forum)

### Tournament Stages
- **0**: None
- **1**: Double Octas
- **2**: Octas
- **3**: Quarters
- **4**: Semis
- **5**: Finals

### Standard Requirements (IDs)
(NEEDS TO BE FIXED)
1. Submit Final Forms
2. Pay Membership Fee
3. Submit Tournament Performance
4. Join an Event
5. Sign Permission Slip
6. Pay Tournament Fees
7. Complete Background Check
8. Respond to Judge Request
9. Complete Judge Training

---

## Contact & Support

For questions or issues with this codebase, email:

sam.nusair@gmail.com

---
