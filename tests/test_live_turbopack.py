import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TurbopackTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DESIGN_TURBOPACK_TEST_PROJECT') and shutil.which('node'),
                         'Set DESIGN_TURBOPACK_TEST_PROJECT to a Next/Babel project for Turbopack checks')
    def test_project_schema_and_loader_contract(self):
        with tempfile.TemporaryDirectory(prefix='turbo-check-', dir=os.environ['DESIGN_TURBOPACK_TEST_PROJECT']) as directory:
            env = dict(os.environ, DESIGN_TURBOPACK_TEST_ROOT=directory)
            if os.name == 'nt':
                q = lambda x: "'" + str(x).replace("'", "''") + "'"
                runner = Path.home() / '.codex/bin/invoke-hidden.ps1'
                command = [shutil.which('pwsh'), '-NoProfile', '-Command',
                           f'& {q(runner)} -FilePath {q(shutil.which("node"))} -ArgumentList @(\'tests/test_live_turbopack.cjs\') -WorkingDirectory {q(ROOT)}']
            else:
                command = [shutil.which('node'), 'tests/test_live_turbopack.cjs']
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
