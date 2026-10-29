import importlib.util
import unittest
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

    def test_scaffold_refuses_inline_whitespace_changes(self):
        with self.assertRaisesRegex(locator.LocatorError, 'inline_source'):
            locator.scaffold('<p>A<span>B</span>C</p>', event('<span>B</span>', 'span'))


if __name__ == '__main__':
    unittest.main()
