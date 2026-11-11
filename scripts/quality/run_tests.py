"""Run integration tests and reject an empty test suite."""
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[2]
suite = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.testsRun:
    print('Error: no tests ran', file=sys.stderr)
    sys.exit(1)
sys.exit(0 if result.wasSuccessful() else 1)
