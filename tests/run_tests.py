#!/usr/bin/env python3
import unittest
import sys
import os

def run_tests():
    """Run all tests in the tests directory"""
    # Get the directory containing this script
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(tests_dir)
    
    # Add project directory to path so we can import the plugin modules
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)
    
    # Add tests directory to path for relative imports
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover(tests_dir, pattern='test_*.py')
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return 0 if tests passed, 1 if any failed
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests()) 