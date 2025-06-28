#!/usr/bin/env python
"""
Comprehensive test runner script for the Genoks multi-tenant API.
Provides different test categories, coverage reporting, and CI/CD integration.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings module for tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.testing')


class TestRunner:
    """Enhanced test runner with multiple execution modes."""
    
    def __init__(self):
        self.project_root = project_root
        self.test_dir = self.project_root / 'tests'
    
    def run_command(self, command, check=True):
        """Run shell command and return result."""
        print(f"Running: {' '.join(command)}")
        try:
            result = subprocess.run(command, check=check, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            if e.stdout:
                print(f"Output: {e.stdout}")
            raise
    
    def run_unit_tests(self, coverage=False, verbose=False):
        """Run unit tests."""
        print("🧪 Running unit tests...")
        
        command = ['pytest', '-m', 'unit or not (integration or slow)']
        
        if verbose:
            command.extend(['-v', '--tb=short'])
        
        if coverage:
            command.extend([
                '--cov=apps',
                '--cov=utils',
                '--cov=middleware',
                '--cov-report=html:htmlcov',
                '--cov-report=term-missing',
                '--cov-fail-under=80'
            ])
        
        return self.run_command(command)
    
    def run_integration_tests(self, verbose=False):
        """Run integration tests."""
        print("🔗 Running integration tests...")
        
        command = ['pytest', '-m', 'integration']
        
        if verbose:
            command.extend(['-v', '--tb=short'])
        
        return self.run_command(command)
    
    def run_security_tests(self, verbose=False):
        """Run security tests."""
        print("🔒 Running security tests...")
        
        command = ['pytest', '-m', 'security']
        
        if verbose:
            command.extend(['-v', '--tb=short'])
        
        return self.run_command(command)
    
    def run_performance_tests(self, verbose=False):
        """Run performance tests."""
        print("⚡ Running performance tests...")
        
        command = ['pytest', '-m', 'performance']
        
        if verbose:
            command.extend(['-v', '--tb=short'])
        
        return self.run_command(command)
    
    def run_tenant_tests(self, verbose=False):
        """Run tenant-specific tests."""
        print("🏢 Running tenant tests...")
        
        command = ['pytest', '-m', 'tenant']
        
        if verbose:
            command.extend(['-v', '--tb=short'])
        
        return self.run_command(command)
    
    def run_all_tests(self, coverage=False, verbose=False, parallel=False):
        """Run all tests."""
        print("🚀 Running all tests...")
        
        command = ['pytest']
        
        if verbose:
            command.extend(['-v', '--tb=short'])
        
        if parallel:
            command.extend(['-n', 'auto'])  # Requires pytest-xdist
        
        if coverage:
            command.extend([
                '--cov=apps',
                '--cov=utils',
                '--cov=middleware',
                '--cov-report=html:htmlcov',
                '--cov-report=term-missing',
                '--cov-report=xml:coverage.xml',
                '--cov-fail-under=75'
            ])
        
        return self.run_command(command)
    
    def run_specific_test(self, test_path, verbose=False):
        """Run specific test file or test method."""
        print(f"🎯 Running specific test: {test_path}")
        
        command = ['pytest', test_path]
        
        if verbose:
            command.extend(['-v', '--tb=short'])
        
        return self.run_command(command)
    
    def run_failed_tests(self, verbose=False):
        """Re-run only failed tests from last run."""
        print("🔄 Re-running failed tests...")
        
        command = ['pytest', '--lf']  # Last failed
        
        if verbose:
            command.extend(['-v', '--tb=short'])
        
        return self.run_command(command)
    
    def run_lint_checks(self):
        """Run code quality checks."""
        print("🔍 Running code quality checks...")
        
        # Black formatting check
        print("Checking code formatting with Black...")
        self.run_command(['black', '--check', '--diff', '.'])
        
        # isort import sorting check
        print("Checking import sorting with isort...")
        self.run_command(['isort', '--check-only', '--diff', '.'])
        
        # flake8 linting
        print("Running flake8 linting...")
        self.run_command(['flake8', '.'])
        
        print("✅ All code quality checks passed!")
    
    def setup_test_environment(self):
        """Setup test environment and database."""
        print("🛠️ Setting up test environment...")
        
        # Create test database if it doesn't exist
        try:
            self.run_command([
                'python', 'manage.py', 'migrate', 
                '--settings=config.settings.testing'
            ])
            print("✅ Test database setup complete!")
        except subprocess.CalledProcessError:
            print("⚠️ Test database setup failed, but continuing...")
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        print("📊 Generating test report...")
        
        # Run tests with detailed reporting
        command = [
            'pytest',
            '--html=test_report.html',
            '--self-contained-html',
            '--cov=apps',
            '--cov=utils',
            '--cov=middleware',
            '--cov-report=html:htmlcov',
            '--cov-report=json:coverage.json',
            '--junit-xml=test_results.xml'
        ]
        
        try:
            self.run_command(command)
            print("✅ Test report generated successfully!")
            print("📄 HTML Report: test_report.html")
            print("📊 Coverage Report: htmlcov/index.html")
            print("📋 JUnit XML: test_results.xml")
        except subprocess.CalledProcessError:
            print("❌ Test report generation failed!")
    
    def run_ci_tests(self):
        """Run tests suitable for CI/CD environment."""
        print("🤖 Running CI/CD tests...")
        
        command = [
            'pytest',
            '--tb=short',
            '--cov=apps',
            '--cov=utils',
            '--cov=middleware',
            '--cov-report=xml:coverage.xml',
            '--cov-report=term',
            '--junit-xml=test_results.xml',
            '--cov-fail-under=70',
            '-x'  # Stop on first failure
        ]
        
        return self.run_command(command)


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description='Genoks API Test Runner')
    
    parser.add_argument(
        'command',
        choices=[
            'unit', 'integration', 'security', 'performance', 'tenant',
            'all', 'failed', 'lint', 'setup', 'report', 'ci', 'specific'
        ],
        help='Test command to run'
    )
    
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Run with coverage reporting'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--parallel', '-p',
        action='store_true',
        help='Run tests in parallel (requires pytest-xdist)'
    )
    
    parser.add_argument(
        '--test-path',
        help='Specific test path for "specific" command'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.command == 'unit':
            runner.run_unit_tests(coverage=args.coverage, verbose=args.verbose)
        
        elif args.command == 'integration':
            runner.run_integration_tests(verbose=args.verbose)
        
        elif args.command == 'security':
            runner.run_security_tests(verbose=args.verbose)
        
        elif args.command == 'performance':
            runner.run_performance_tests(verbose=args.verbose)
        
        elif args.command == 'tenant':
            runner.run_tenant_tests(verbose=args.verbose)
        
        elif args.command == 'all':
            runner.run_all_tests(
                coverage=args.coverage, 
                verbose=args.verbose,
                parallel=args.parallel
            )
        
        elif args.command == 'failed':
            runner.run_failed_tests(verbose=args.verbose)
        
        elif args.command == 'lint':
            runner.run_lint_checks()
        
        elif args.command == 'setup':
            runner.setup_test_environment()
        
        elif args.command == 'report':
            runner.generate_test_report()
        
        elif args.command == 'ci':
            runner.run_ci_tests()
        
        elif args.command == 'specific':
            if not args.test_path:
                print("❌ --test-path is required for 'specific' command")
                sys.exit(1)
            runner.run_specific_test(args.test_path, verbose=args.verbose)
        
        print("✅ Test execution completed successfully!")
        
    except subprocess.CalledProcessError:
        print("❌ Test execution failed!")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Test execution interrupted by user")
        sys.exit(1)


if __name__ == '__main__':
    main() 