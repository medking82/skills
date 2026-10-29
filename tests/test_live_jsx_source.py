import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class JsxSourceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for JSX bridge checks')
    def test_jsx_boundaries_and_optional_project_compiler(self):
        project = os.environ.get('DESIGN_JSX_TEST_PROJECT')
        parent = Path(project) if project else ROOT / 'tests'
        with tempfile.TemporaryDirectory(prefix='jsx-source-', dir=parent) as directory:
            env = dict(os.environ, DESIGN_JSX_TEST_ROOT=directory)
            if project:
                env['DESIGN_JSX_WITH_COMPILER'] = '1'
            if os.name == 'nt':
                q = lambda s: "'" + str(s).replace("'", "''") + "'"
                runner = Path.home() / '.codex/bin/invoke-hidden.ps1'
                command = [shutil.which('pwsh'), '-NoProfile', '-Command',
                           f'& {q(runner)} -FilePath {q(shutil.which("node"))} -ArgumentList @(\'tests/test_live_jsx_source.cjs\') -WorkingDirectory {q(ROOT)}']
            else:
                command = [shutil.which('node'), 'tests/test_live_jsx_source.cjs']
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                                    timeout=30, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
