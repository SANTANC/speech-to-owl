import unittest
import xmlrunner
import os

if __name__ == "__main__":
    # Discover tests within the Project_Files package
    start_dir = os.path.dirname(__file__)
    suite = unittest.defaultTestLoader.discover(start_dir, pattern="test_*.py")
    # Output directory for JUnit XML reports
    reports_dir = os.path.join(start_dir, "test-reports")
    os.makedirs(reports_dir, exist_ok=True)
    runner = xmlrunner.XMLTestRunner(output=reports_dir, verbosity=2)
    result = runner.run(suite)
    # Exit non-zero if failures/errors to signal CI
    exit_code = 0 if result.wasSuccessful() else 1
    raise SystemExit(exit_code)
