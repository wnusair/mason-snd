# Testing Infrastructure

This directory contains the comprehensive testing system for the mason-snd Flask application.

## Directory Structure

- `terminal_tests/` - Command-line runnable unit tests for all critical routes and functions
- `web_dashboard/` - Web-based testing dashboard with visual results and test management
- `mock_data/` - Mock data generators and test fixtures
- `test_databases/` - Isolated test database copies and management utilities

## Key Features

1. **Database Isolation**: All tests run on cloned databases to prevent interference with production data
2. **Comprehensive Coverage**: Tests for all major routes, models, and business logic
3. **Mock Tournament Simulation**: End-to-end tournament flow testing
4. **Web Dashboard**: Visual test runner with success rates and detailed failure reporting
5. **Automatic Cleanup**: All test data is automatically removed after testing

## Usage

### Terminal Tests
```bash
python -m UNIT_TEST.run_terminal_tests
```

### Web Dashboard
Access the testing dashboard at `/test_dashboard` when the application is running in test mode.

### Mock Tournament Flow
The system can simulate complete tournament workflows including:
- User registration and judge assignment
- Event creation and participant management
- Tournament creation and roster generation
- Score simulation and metrics calculation