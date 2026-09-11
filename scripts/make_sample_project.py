"""Create a harmless sample Git project for trying the code workflow before real repositories.

Usage: python scripts/make_sample_project.py C:\\path\\to\\sample-project
Prints the code_projects entry to paste into the private config.json (game or business)."""
import json
import subprocess
import sys
from pathlib import Path

target = Path(sys.argv[1] if len(sys.argv) > 1 else 'assistant-sample-project').resolve()
if target.exists() and any(target.iterdir()):
    sys.exit('Target folder must be empty or new')
(target / 'app').mkdir(parents=True)
(target / 'tests').mkdir()
(target / 'app' / 'calc.py').write_text('def average(xs):\n    return sum(xs) / len(xs)\n')
(target / 'tests' / 'test_calc.py').write_text(
    'import unittest\nfrom app.calc import average\n\n'
    'class T(unittest.TestCase):\n    def test_average(self):\n        self.assertEqual(average([2, 4]), 3)\n\n'
    'if __name__ == "__main__":\n    unittest.main()\n')
(target / 'app' / '__init__.py').write_text('')
(target / 'tests' / '__init__.py').write_text('')
for cmd in (['init', '-q'], ['add', '.'],
            ['-c', 'user.name=Sample', '-c', 'user.email=sample@localhost', 'commit', '-qm', 'Sample project']):
    subprocess.run(['git', '-C', str(target), *cmd], check=True)
print(json.dumps({'execution_enabled': True, 'source': str(target), 'allowed_prefixes': ['app/', 'tests/'],
                  'context_files': ['app/calc.py', 'tests/test_calc.py'],
                  'checks': [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']],
                  'check_timeout_seconds': 120}, indent=2))
print('\nSuggested first task: "Make average([]) return None instead of crashing, with a regression test."')
