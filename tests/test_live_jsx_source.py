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
        self.run_script('test_live_jsx_source.cjs')

    @unittest.skipUnless(os.environ.get('DESIGN_JSX_TEST_PROJECT') and shutil.which('node'), 'Project Babel/React are required')
    def test_shared_instance_scopes(self):
        self.run_script('test_live_jsx_instances.cjs')

    def run_script(self, script):
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
                           f'& {q(runner)} -FilePath {q(shutil.which("node"))} -ArgumentList @({q("tests/" + script)}) -WorkingDirectory {q(ROOT)}']
            else:
                command = [shutil.which('node'), 'tests/' + script]
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                                    timeout=30, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
