"""Opt-in regression against the pinned native engine, without a browser or server."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('locator', ROOT / 'skills/impeccable/scripts/live-locate.py')
locator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locator)


@unittest.skipUnless(os.name == 'nt' and os.environ.get('IMPECCABLE_TEST_ENGINE_WRAPPER'),
                     'Set IMPECCABLE_TEST_ENGINE_WRAPPER for native Windows engine regression')
class NativeLocatorTests(unittest.TestCase):
    def run_ps(self, command, cwd):
        result = subprocess.run([shutil.which('pwsh'), '-NoProfile', '-Command', command],
                                cwd=cwd, capture_output=True, text=True, encoding='utf-8',
                                creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    @staticmethod
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    def test_native_accept_and_discard_preserve_minified_neighbors(self):
        runner = Path.home() / '.codex/bin/invoke-hidden.ps1'
        wrapper = Path(os.environ['IMPECCABLE_TEST_ENGINE_WRAPPER']).resolve()
        with tempfile.TemporaryDirectory(prefix='locator-native-', dir=ROOT / 'tests') as directory:
            cwd = Path(directory)
            q = self.quote
            for args in (['init', '-q'], ['add', 'index.html']):
                if args[0] == 'add':
                    (cwd / 'index.html').write_text('<html><body></body></html>', encoding='utf-8')
                self.run_ps(f'& {q(runner)} -FilePath {q(shutil.which("git"))} -ArgumentList @('
                            + ','.join(map(q, args)) + f') -WorkingDirectory {q(cwd)}', cwd)
            baseline = '<!doctype html><html><body>前<section><h2>Target</h2><p>Keep</p></section>后</body></html>'
            for discard in (False, True):
                session = '1234abcd' if discard else 'abcd1234'
                event = dict(id=session, count=1, element=dict(tagName='h2', outerHTML='<h2>Target</h2>'))
                scaffold = locator.scaffold(baseline, event)
                block = scaffold['wrapperBlock'].replace('<!-- Variants: insert below this line -->',
                        '<div data-impeccable-variant="1"><h2>Chosen</h2></div>')
                text = baseline[:scaffold['replaceStartOffset']] + block + baseline[scaffold['replaceEndOffset']:]
                (cwd / 'index.html').write_bytes(text.encode('utf-8'))
                args = ['live-accept', '--id', session] + (['--discard'] if discard else ['--variant', '1'])
                output = self.run_ps(f'& {q(wrapper)} -EngineArguments @(' + ','.join(map(q, args)) + ')', cwd)
                self.assertTrue(json.loads(output)['handled'])
                result = (cwd / 'index.html').read_text(encoding='utf-8')
                self.assertIn('<html><body>前<section>', result)
                self.assertIn('<p>Keep</p></section>后</body></html>', result)
                self.assertIn('<h2>Target</h2>' if discard else '<h2>Chosen</h2>', result)
                self.assertNotIn('impeccable-variant', result)


if __name__ == '__main__':
    unittest.main()
