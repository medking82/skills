import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CaptureScriptTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for browser capture unit checks')
    def test_session_capture_and_disposal(self):
        node = shutil.which('node')
        if os.name == 'nt':
            quote = lambda x: "'" + str(x).replace("'", "''") + "'"
            runner = Path.home() / '.codex/bin/invoke-hidden.ps1'
            command = [shutil.which('pwsh'), '-NoProfile', '-Command',
                       f'& {quote(runner)} -FilePath {quote(node)} -ArgumentList @(\'tests/test_capture_live_selection.cjs\') -WorkingDirectory {quote(ROOT)}']
        else:
            command = [node, 'tests/test_capture_live_selection.cjs']
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=20,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
