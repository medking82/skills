import importlib.util
import unittest
import tempfile
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('locator', ROOT / 'skills/impeccable/scripts/live-locate.py')
locator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locator)


def event(html, tag='h2', parent=''):
    return dict(id='abc12345', count=3, element=dict(outerHTML=html, tagName=tag, parentContext=parent))


class LiveLocatorTests(unittest.TestCase):
    def test_minified_nested_unicode_and_crlf_preserve_surroundings(self):
        source = '\ufeff<html>\r\n<body>中文前<h2>Sample <em>Card</em></h2>后</body></html>'
        result = locator.scaffold(source, event('<h2>Sample <em>Card</em></h2>'))
        start, end = result['replaceStartOffset'], result['replaceEndOffset']
        self.assertEqual(source[start:end], '<h2>Sample <em>Card</em></h2>')
        assembled = source[:start] + result['wrapperBlock'] + source[end:]
        self.assertTrue(assembled.startswith('\ufeff<html>\r\n<body>中文前'))
        self.assertTrue(assembled.endswith('后</body></html>'))
        self.assertIn('data-impeccable-variant="original"', assembled)
        self.assertFalse(result['sourceWritten'])
        self.assertTrue(result['wrapperBlock'].startswith('\n<!--'))
        self.assertTrue(result['wrapperBlock'].endswith('-->\n'))

    def test_entities_and_attribute_serialization(self):
        source = "<h2 title='A &amp; B'>A &amp; B</h2>"
        self.assertEqual(locator.locate(source, event('<h2 title="A &amp; B">A &amp; B</h2>')), (0, len(source)))

    def test_duplicate_refuses_without_context(self):
        with self.assertRaisesRegex(locator.LocatorError, 'element_ambiguous'):
            locator.locate('<h2>X</h2><h2>X</h2>', event('<h2>X</h2>'))

    def test_parent_context_selects_only_matching_region(self):
        source = '<section id="a"><h2>X</h2></section><section id="b"><h2>X</h2></section>'
        start, end = locator.locate(source, event('<h2>X</h2>', parent='<section id="b">'))
        self.assertEqual(start, source.rindex('<h2>'))
        self.assertEqual(source[start:end], '<h2>X</h2>')

    def test_identical_siblings_still_refuse_with_parent(self):
        with self.assertRaisesRegex(locator.LocatorError, 'element_ambiguous'):
            locator.locate('<section id="a"><h2>X</h2><h2>X</h2></section>', event('<h2>X</h2>', parent='<section id="a">'))

    def test_script_and_comments_are_not_elements(self):
        with self.assertRaisesRegex(locator.LocatorError, 'element_not_found'):
            locator.locate('<script>"<h2>X</h2>"</script><!-- <h2>X</h2> -->', event('<h2>X</h2>'))

    def test_raw_text_containers_do_not_supply_fake_targets(self):
        with self.assertRaisesRegex(locator.LocatorError, 'element_not_found'):
            locator.locate('<textarea><h2>X</h2></textarea><title><h2>X</h2></title>', event('<h2>X</h2>'))

    def test_malformed_and_non_html_self_closing_refuse(self):
        for source in ('<h2>X</div>', '<div/>', '<h2>X'):
            with self.subTest(source=source), self.assertRaises(locator.LocatorError):
                locator.locate(source, event('<h2>X</h2>'))

    def test_textless_void_element(self):
        source = '<p>A<img src="a.png" alt="">B</p>'
        a, b = locator.locate(source, event('<img src="a.png" alt="">', 'img'))
        self.assertEqual(source[a:b], '<img src="a.png" alt="">')

    def test_inline_scaffold_is_detached_without_added_whitespace(self):
        result = locator.scaffold('<p>A<span>B</span>C</p>', event('<span>B</span>', 'span'))
        self.assertFalse(result['publishToSource'])
        self.assertNotIn('\n', result['wrapperBlock'])

    def test_repeated_sibling_uses_captured_dom_path(self):
        parent = '<p>A<span>X</span><span>X</span>B</p>'
        source = '<html><body>' + parent + '</body></html>'
        e = event('<span>X</span>', 'span')
        e['sourceLocator'] = dict(path=[dict(tag='p', index=0), dict(tag='span', index=1)], parentHTML=parent)
        a, b = locator.locate(source, e)
        self.assertEqual(a, source.rindex('<span>'))
        self.assertEqual(source[a:b], '<span>X</span>')
        e['sourceLocator']['parentHTML'] = '<p>Changed<span>X</span><span>X</span>B</p>'
        with self.assertRaisesRegex(locator.LocatorError, 'parent_mismatch'):
            locator.locate(source, e)

    def test_inline_apply_preserves_exact_neighbor_bytes_and_refuses_drift(self):
        source = '\ufeff<html>\r\n<body><p>A<span>X</span>B &amp; 中文</p></body></html>'
        with tempfile.TemporaryDirectory(prefix='inline-locator-', dir=ROOT / 'tests') as directory:
            path = Path(directory) / 'index.html'
            path.write_bytes(source.encode('utf-8'))
            receipt = locator.scaffold(source, event('<span>X</span>', 'span'))
            receipt['file'] = str(path)
            with self.assertRaisesRegex(locator.LocatorError, 'session_mismatch'):
                locator.apply_selection(path, receipt, '<span>Wrong</span>', 'badbad00')
            self.assertEqual(path.read_bytes(), source.encode('utf-8'))
            locator.apply_selection(path, receipt, '<span>Chosen</span>', receipt['sessionId'])
            self.assertEqual(path.read_bytes(), source.replace('<span>X</span>', '<span>Chosen</span>').encode('utf-8'))
            before = path.read_bytes()
            with self.assertRaisesRegex(locator.LocatorError, 'source_changed'):
                locator.apply_selection(path, receipt, '<span>Wrong</span>', receipt['sessionId'])
            self.assertEqual(path.read_bytes(), before)

    def test_template_commit_requires_matching_validation_and_preserves_neighbors(self):
        source="const label='X'; const node=<span>{label}</span>; // Keep\r\n"
        original='<span>{label}</span>'
        replacement='<span className="chosen">{label}</span>'
        with tempfile.TemporaryDirectory(prefix='template-commit-',dir=ROOT/'tests') as directory:
            path=Path(directory)/'Panel.jsx';path.write_bytes(source.encode('utf-8'))
            receipt=dict(publishToSource=False,sourceKind='jsx',sessionId='abc12345',file=str(path),
                         sourceSha256=hashlib.sha256(source.encode('utf-8')).hexdigest(),
                         replaceStartOffset=source.index(original),replaceEndOffset=source.index(original)+len(original),original=original)
            with self.assertRaisesRegex(locator.LocatorError,'template_validation'):
                locator.apply_selection(path,receipt,replacement,'abc12345')
            self.assertEqual(path.read_bytes(),source.encode('utf-8'))
            validation=dict(ok=True,validator='babel-jsx-static-edits-v1',receipt=receipt,
                            replacementSha256=hashlib.sha256(replacement.encode('utf-8')).hexdigest())
            with self.assertRaisesRegex(locator.LocatorError,'template_validation'):
                locator.apply_selection(path,receipt,replacement+' ','abc12345',validation)
            locator.apply_selection(path,receipt,replacement,'abc12345',validation)
            self.assertEqual(path.read_bytes(),source.replace(original,replacement).encode('utf-8'))


if __name__ == '__main__':
    unittest.main()
