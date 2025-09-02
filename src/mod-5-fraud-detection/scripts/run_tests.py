#!/usr/bin/env python3
"""Test runner for UberEats Fraud Detection System.

Runs comprehensive security, performance, and integration tests
with detailed reporting and benchmarking.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestRunner:
    """Comprehensive test runner with reporting."""
    
    def __init__(self):
        """Initialize test runner."""
        self.results: Dict[str, Any] = {
            "start_time": time.time(),
            "tests": {},
            "summary": {},
            "errors": []
        }
    
    def run_security_tests(self) -> bool:
        """Run security test suite."""
        print("🔒 Running Security Tests...")
        print("=" * 50)
        
        try:
            # Run security tests
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                "tests/security/test_security_suite.py",
                "-v", "--tb=short", "--no-header"
            ], capture_output=True, text=True, cwd=PROJECT_ROOT)
            
            success = result.returncode == 0
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            self.results["tests"]["security"] = {
                "success": success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            if success:
                print("✅ Security tests PASSED")
            else:
                print("❌ Security tests FAILED")
                
            return success
            
        except Exception as e:
            print(f"❌ Error running security tests: {e}")
            self.results["errors"].append(f"Security tests error: {e}")
            return False
    
    def run_performance_tests(self) -> bool:
        """Run performance test suite."""
        print("\n⚡ Running Performance Tests...")
        print("=" * 50)
        
        try:
            # Run performance tests with more detailed output
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                "tests/performance/test_performance_suite.py",
                "-v", "--tb=short", "--no-header", "-s"
            ], capture_output=True, text=True, cwd=PROJECT_ROOT)
            
            success = result.returncode == 0
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            self.results["tests"]["performance"] = {
                "success": success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            if success:
                print("✅ Performance tests PASSED")
            else:
                print("❌ Performance tests FAILED")
                
            return success
            
        except Exception as e:
            print(f"❌ Error running performance tests: {e}")
            self.results["errors"].append(f"Performance tests error: {e}")
            return False
    
    def run_syntax_checks(self) -> bool:
        """Run syntax checks on all Python files."""
        print("\n🐍 Running Syntax Checks...")
        print("=" * 50)
        
        python_files = []
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Skip test files and __pycache__
            if "__pycache__" in root or ".pytest_cache" in root or ".venv" in root:
                continue
                
            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)
        
        failed_files = []
        
        for py_file in python_files:
            try:
                result = subprocess.run([
                    sys.executable, "-m", "py_compile", str(py_file)
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    failed_files.append((py_file, result.stderr))
                    print(f"❌ {py_file}: {result.stderr}")
                else:
                    print(f"✅ {py_file}")
            except Exception as e:
                failed_files.append((py_file, str(e)))
                print(f"❌ {py_file}: {e}")
        
        success = len(failed_files) == 0
        
        self.results["tests"]["syntax"] = {
            "success": success,
            "total_files": len(python_files),
            "failed_files": len(failed_files),
            "failures": failed_files
        }
        
        if success:
            print(f"✅ All {len(python_files)} Python files have valid syntax")
        else:
            print(f"❌ {len(failed_files)} of {len(python_files)} files failed syntax check")
        
        return success
    
    def run_import_tests(self) -> bool:
        """Test that all modules can be imported."""
        print("\n📦 Running Import Tests...")
        print("=" * 50)
        
        test_imports = [
            "src.utils.circuit_breaker",
            "src.utils.input_validator", 
            "src.utils.retry_handler",
            "src.security.secrets_manager",
            "src.monitoring.system_monitor"
        ]
        
        failed_imports = []
        
        for module in test_imports:
            try:
                __import__(module)
                print(f"✅ {module}")
            except Exception as e:
                failed_imports.append((module, str(e)))
                print(f"❌ {module}: {e}")
        
        success = len(failed_imports) == 0
        
        self.results["tests"]["imports"] = {
            "success": success,
            "total_modules": len(test_imports),
            "failed_imports": len(failed_imports),
            "failures": failed_imports
        }
        
        return success
    
    def check_security_configuration(self) -> bool:
        """Check security configuration."""
        print("\n🔐 Checking Security Configuration...")
        print("=" * 50)
        
        security_issues = []
        
        # Check for .env files in repo
        env_files = list(PROJECT_ROOT.glob("**/.env"))
        if env_files:
            for env_file in env_files:
                security_issues.append(f".env file found in repo: {env_file}")
                print(f"⚠️  .env file found: {env_file}")
        
        # Check for hardcoded credentials in Python files
        credential_patterns = [
            "password.*=.*['\"][^'\"]{10,}['\"]",
            "api.*key.*=.*['\"]sk-[^'\"]+['\"]",
            "secret.*=.*['\"][^'\"]{15,}['\"]"
        ]
        
        for py_file in PROJECT_ROOT.glob("**/*.py"):
            if "__pycache__" in str(py_file) or ".venv" in str(py_file):
                continue
                
            try:
                content = py_file.read_text()
                for pattern in credential_patterns:
                    import re
                    if re.search(pattern, content, re.IGNORECASE):
                        security_issues.append(f"Potential hardcoded credential in {py_file}")
                        print(f"⚠️  Potential credential in {py_file}")
                        break
            except Exception:
                continue
        
        # Check .gitignore exists
        gitignore = PROJECT_ROOT / ".gitignore"
        if not gitignore.exists():
            security_issues.append(".gitignore file missing")
            print("⚠️  .gitignore file missing")
        else:
            gitignore_content = gitignore.read_text()
            required_entries = [".env", "*.log", "__pycache__"]
            for entry in required_entries:
                if entry not in gitignore_content:
                    security_issues.append(f".gitignore missing entry: {entry}")
                    print(f"⚠️  .gitignore missing: {entry}")
        
        success = len(security_issues) == 0
        
        self.results["tests"]["security_config"] = {
            "success": success,
            "issues": security_issues
        }
        
        if success:
            print("✅ Security configuration looks good")
        else:
            print(f"⚠️  {len(security_issues)} security configuration issues found")
        
        return success
    
    def generate_report(self):
        """Generate final test report."""
        print("\n📊 TEST REPORT")
        print("=" * 50)
        
        total_duration = time.time() - self.results["start_time"]
        
        # Count successes/failures
        tests = self.results["tests"]
        total_tests = len(tests)
        passed_tests = sum(1 for t in tests.values() if t.get("success", False))
        failed_tests = total_tests - passed_tests
        
        print(f"Duration: {total_duration:.2f}s")
        print(f"Total Test Suites: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        
        if self.results["errors"]:
            print(f"Errors: {len(self.results['errors'])}")
        
        print("\nTest Suite Results:")
        for test_name, result in tests.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        # Overall status
        overall_success = failed_tests == 0 and len(self.results["errors"]) == 0
        
        print(f"\n{'🎉 ALL TESTS PASSED!' if overall_success else '❌ SOME TESTS FAILED'}")
        
        return overall_success


def main():
    """Run the complete test suite."""
    print("🚀 UberEats Fraud Detection System - Test Suite")
    print("=" * 60)
    
    runner = TestRunner()
    
    # Run all test suites
    syntax_ok = runner.run_syntax_checks()
    imports_ok = runner.run_import_tests()
    security_config_ok = runner.check_security_configuration()
    security_ok = runner.run_security_tests()
    performance_ok = runner.run_performance_tests()
    
    # Generate final report
    overall_success = runner.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()