# Copilot Instructions for mason-snd

## Project Overview
- **mason-snd** is a Flask-based web application for tournament and event management, featuring robust user, admin, and tournament workflows.
- The codebase emphasizes **production safety**: all testing and development operations are strictly isolated from production data.

## Architecture & Key Components
- Main app code: `mason_snd/` (routes, models, templates, static files)
- Testing system: `UNIT_TEST/` (see below)
- Database: SQLite, with migration scripts in `migrations/`
- Tests: `tests/` (legacy and integration scripts)
- Tutorials and examples: `tutorial/`

## Testing System (UNIT_TEST)
- **Production Safety**: All tests run on isolated database copies. Safety guards prevent any production data modification.
- **Test orchestration**: Use `UNIT_TEST/master_controller.py` for running quick or full test suites.
- **Verification**: Run `UNIT_TEST/final_verification.py --verify` before deployment or after major changes.
- **Web dashboard**: Enable with `ENABLE_TESTING=True` and access `/test_dashboard` in dev mode.
- **Emergency cleanup**: Use `UNIT_TEST/production_safety.py --cleanup` to remove all test data.
- **Configuration**: Set environment variables (`ENABLE_TESTING`, `TEST_DB_PATH`, `TEST_DEBUG`) for test control.

## Developer Workflows
- **Run quick tests**: `python UNIT_TEST/master_controller.py --quick`
- **Run full tests**: `python UNIT_TEST/master_controller.py --full`
- **Terminal tests**: `python UNIT_TEST/run_tests.py`
- **Verify safety**: `python UNIT_TEST/production_safety.py --check`
- **Generate reports**: `python UNIT_TEST/final_verification.py --verify --report`

## Integration Patterns
- To integrate testing with Flask, use:
  ```python
  from UNIT_TEST.integration import integrate_testing_with_app
  if app.config.get('ENABLE_TESTING', False):
      integrate_testing_with_app(app)
  ```
- Add CLI commands for tests and verification in your Flask app as shown in `README_UPDATED.md`.

## Project-Specific Conventions
- **Never run tests against production database**; all test operations are validated for safety.
- **Automatic cleanup** is recommended after all test runs.
- **Detailed logging** and error handling are built-in; check logs for troubleshooting.
- **Mock tournament simulation** is available for end-to-end workflow testing.

## Key Files & Directories
- `mason_snd/` — main app code
- `UNIT_TEST/` — testing system (see `README_UPDATED.md` for details)
- `requirements.txt` — dependencies
- `tests/` — additional scripts and integration tests
- `tutorial/` — onboarding and example code

## Example Commands
- Run all tests: `python UNIT_TEST/master_controller.py --full`
- Emergency cleanup: `python UNIT_TEST/production_safety.py --cleanup`
- Access dashboard: set `ENABLE_TESTING=True` and visit `/test_dashboard`

## Safety & Troubleshooting
- Always verify safety before and after running tests.
- Use emergency cleanup utilities if any test artifacts remain.
- Review logs for error details and recovery procedures.

---

For more details, see `UNIT_TEST/README_UPDATED.md` and in-code comments in `UNIT_TEST/` modules.
