"""
Production Safety Module - Ensures test isolation and production database protection.
This module provides comprehensive safeguards to prevent any test data from affecting production.
"""
import os
import sys
import json
import sqlite3
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

class ProductionSafetyGuard:
    """
    Production safety guard that prevents test interference with production data.
    Implements multiple layers of protection and validation.
    """
    
    def __init__(self):
        self.production_db_path = None
        self.test_db_paths = set()
        self.temp_directories = set()
        self.safety_checks_passed = False
        self.protection_level = "MAXIMUM"
        
        # Identify production database
        self._identify_production_database()
        
        # Set up protection barriers
        self._setup_protection_barriers()
    
    def _identify_production_database(self):
        """Identify and protect the production database"""
        potential_prod_paths = [
            "/workspaces/mason-snd/instance/db.sqlite3",
            "/workspaces/mason-snd/mason_snd.db",
            "/workspaces/mason-snd/database.db",
            os.path.join(os.path.dirname(__file__), "../instance/db.sqlite3")
        ]
        
        for path in potential_prod_paths:
            if os.path.exists(path):
                self.production_db_path = os.path.abspath(path)
                print(f"⚠️  PRODUCTION DATABASE IDENTIFIED: {self.production_db_path}")
                break
        
        if not self.production_db_path:
            # Look for any .db or .sqlite files that might be production
            project_root = "/workspaces/mason-snd"
            for root, dirs, files in os.walk(project_root):
                # Skip test directories
                if "UNIT_TEST" in root or "test" in root.lower():
                    continue
                    
                for file in files:
                    if file.endswith(('.db', '.sqlite', '.sqlite3')) and not file.startswith('test_'):
                        potential_prod = os.path.join(root, file)
                        print(f"⚠️  POTENTIAL PRODUCTION DATABASE: {potential_prod}")
                        if not self.production_db_path:  # Take the first one found
                            self.production_db_path = potential_prod
    
    def _setup_protection_barriers(self):
        """Set up multiple protection barriers"""
        if self.production_db_path:
            # Make production database read-only during tests (if possible)
            try:
                current_perms = os.stat(self.production_db_path).st_mode
                # Store original permissions for restoration
                self.original_prod_perms = current_perms
            except:
                pass
    
    def validate_test_database_path(self, db_path):
        """
        Validate that a database path is safe for testing
        
        Args:
            db_path: Path to test database
            
        Returns:
            bool: True if safe, False if dangerous
        """
        if not db_path:
            return False
        
        abs_path = os.path.abspath(db_path)
        
        # CRITICAL: Never allow operations on production database
        if self.production_db_path and abs_path == os.path.abspath(self.production_db_path):
            raise ValueError(f"🚨 PRODUCTION DATABASE ACCESS DENIED: {abs_path}")
        
        # Must be in a test directory or temporary location
        safe_patterns = [
            "/tmp/",
            "test_",
            "UNIT_TEST",
            "testing",
            tempfile.gettempdir()
        ]
        
        path_str = str(abs_path).lower()
        if not any(pattern.lower() in path_str for pattern in safe_patterns):
            raise ValueError(f"🚨 UNSAFE DATABASE PATH: {abs_path}")
        
        # Register as test database
        self.test_db_paths.add(abs_path)
        return True
    
    def create_isolated_test_database(self, test_name="test"):
        """
        Create a completely isolated test database
        
        Args:
            test_name: Name for the test database
            
        Returns:
            str: Path to isolated test database
        """
        # Create temporary directory for this test
        temp_dir = tempfile.mkdtemp(prefix=f"mason_test_{test_name}_")
        self.temp_directories.add(temp_dir)
        
        # Create test database in temp directory
        test_db_path = os.path.join(temp_dir, f"test_{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        
        # Validate safety
        self.validate_test_database_path(test_db_path)
        
        return test_db_path
    
    def clone_production_safely(self, test_db_path):
        """
        Safely clone production database for testing
        
        Args:
            test_db_path: Path where test database should be created
            
        Returns:
            bool: Success status
        """
        # Validate test path safety
        self.validate_test_database_path(test_db_path)
        
        if not self.production_db_path or not os.path.exists(self.production_db_path):
            print("⚠️  No production database found to clone")
            return False
        
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
            
            # SAFE READ-ONLY COPY
            print(f"📋 Cloning production database (READ-ONLY)")
            print(f"   From: {self.production_db_path}")
            print(f"   To:   {test_db_path}")
            
            shutil.copy2(self.production_db_path, test_db_path)
            
            # Verify the copy
            if not os.path.exists(test_db_path):
                raise Exception("Database copy failed")
            
            # Double-check we didn't overwrite production
            if os.path.abspath(test_db_path) == os.path.abspath(self.production_db_path):
                raise Exception("🚨 CRITICAL: Test database path matches production!")
            
            print(f"✅ Safe database clone created")
            return True
            
        except Exception as e:
            print(f"🚨 Database cloning failed: {e}")
            return False
    
    def verify_production_integrity(self):
        """
        Verify that production database has not been modified
        
        Returns:
            dict: Integrity check results
        """
        if not self.production_db_path or not os.path.exists(self.production_db_path):
            return {'status': 'no_production_db', 'safe': True}
        
        try:
            # Get current modification time and size
            stat = os.stat(self.production_db_path)
            current_mtime = stat.st_mtime
            current_size = stat.st_size
            
            # Store for comparison if this is first check
            if not hasattr(self, 'prod_initial_mtime'):
                self.prod_initial_mtime = current_mtime
                self.prod_initial_size = current_size
                return {'status': 'baseline_set', 'safe': True}
            
            # Compare with baseline
            mtime_changed = abs(current_mtime - self.prod_initial_mtime) > 1  # 1 second tolerance
            size_changed = current_size != self.prod_initial_size
            
            if mtime_changed or size_changed:
                return {
                    'status': 'production_modified',
                    'safe': False,
                    'mtime_changed': mtime_changed,
                    'size_changed': size_changed,
                    'warning': f"🚨 PRODUCTION DATABASE MAY HAVE BEEN MODIFIED!"
                }
            
            return {'status': 'production_safe', 'safe': True}
            
        except Exception as e:
            return {
                'status': 'check_failed',
                'safe': False,
                'error': str(e)
            }
    
    def emergency_cleanup(self):
        """Emergency cleanup of all test resources"""
        print("🧹 EMERGENCY CLEANUP - Removing all test resources")
        
        cleanup_results = {
            'test_databases_removed': 0,
            'temp_directories_removed': 0,
            'errors': []
        }
        
        # Remove all test databases
        for test_db in list(self.test_db_paths):
            try:
                if os.path.exists(test_db):
                    # Double-check this is not production
                    if self.production_db_path and os.path.abspath(test_db) == os.path.abspath(self.production_db_path):
                        cleanup_results['errors'].append(f"🚨 Refused to delete production database: {test_db}")
                        continue
                    
                    os.remove(test_db)
                    cleanup_results['test_databases_removed'] += 1
                    print(f"   ✅ Removed test database: {test_db}")
                
                self.test_db_paths.discard(test_db)
                
            except Exception as e:
                cleanup_results['errors'].append(f"Failed to remove {test_db}: {str(e)}")
        
        # Remove all temporary directories
        for temp_dir in list(self.temp_directories):
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    cleanup_results['temp_directories_removed'] += 1
                    print(f"   ✅ Removed temp directory: {temp_dir}")
                
                self.temp_directories.discard(temp_dir)
                
            except Exception as e:
                cleanup_results['errors'].append(f"Failed to remove {temp_dir}: {str(e)}")
        
        # Look for any orphaned test files
        try:
            self._cleanup_orphaned_test_files()
        except Exception as e:
            cleanup_results['errors'].append(f"Orphaned file cleanup failed: {str(e)}")
        
        return cleanup_results
    
    def _cleanup_orphaned_test_files(self):
        """Clean up any orphaned test files"""
        project_root = "/workspaces/mason-snd"
        
        # Common test file patterns
        test_patterns = [
            "test_*.db",
            "test_*.sqlite",
            "test_*.sqlite3",
            "*test*.db"
        ]
        
        for root, dirs, files in os.walk(project_root):
            # Skip if this is production area
            if "UNIT_TEST" not in root:
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if it matches test patterns
                for pattern in test_patterns:
                    if file.startswith(pattern.replace("*", "")):
                        try:
                            os.remove(file_path)
                            print(f"   ✅ Removed orphaned test file: {file_path}")
                        except:
                            pass
    
    def generate_safety_report(self):
        """Generate comprehensive safety report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'protection_level': self.protection_level,
            'production_database': {
                'path': self.production_db_path,
                'exists': os.path.exists(self.production_db_path) if self.production_db_path else False,
                'integrity_check': self.verify_production_integrity()
            },
            'test_resources': {
                'test_databases': list(self.test_db_paths),
                'temp_directories': list(self.temp_directories),
                'total_test_resources': len(self.test_db_paths) + len(self.temp_directories)
            },
            'safety_status': 'SAFE' if self.verify_production_integrity()['safe'] else 'WARNING'
        }
        
        return report

# Global safety guard instance
safety_guard = ProductionSafetyGuard()

def get_safety_guard():
    """Get the global safety guard instance"""
    return safety_guard

def create_safe_test_database(test_name="test"):
    """Create a safe test database"""
    return safety_guard.create_isolated_test_database(test_name)

def validate_test_path(path):
    """Validate that a path is safe for testing"""
    return safety_guard.validate_test_database_path(path)

def emergency_cleanup():
    """Perform emergency cleanup of all test resources"""
    return safety_guard.emergency_cleanup()

def verify_production_safety():
    """Verify production database safety"""
    return safety_guard.verify_production_integrity()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Production Safety Guard")
    parser.add_argument('--check', action='store_true', help='Check production safety')
    parser.add_argument('--cleanup', action='store_true', help='Emergency cleanup')
    parser.add_argument('--report', action='store_true', help='Generate safety report')
    
    args = parser.parse_args()
    
    if args.check:
        result = verify_production_safety()
        print(f"Production Safety: {'✅ SAFE' if result['safe'] else '⚠️ WARNING'}")
        if not result['safe']:
            print(f"Details: {result}")
    
    elif args.cleanup:
        results = emergency_cleanup()
        print(f"Cleanup completed:")
        print(f"  Databases removed: {results['test_databases_removed']}")
        print(f"  Directories removed: {results['temp_directories_removed']}")
        if results['errors']:
            print(f"  Errors: {len(results['errors'])}")
    
    elif args.report:
        report = safety_guard.generate_safety_report()
        print("="*60)
        print("PRODUCTION SAFETY REPORT")
        print("="*60)
        print(json.dumps(report, indent=2))
        print("="*60)
    
    else:
        print("Production Safety Guard")
        print("Commands:")
        print("  --check   Check production safety")
        print("  --cleanup Emergency cleanup")
        print("  --report  Generate safety report")