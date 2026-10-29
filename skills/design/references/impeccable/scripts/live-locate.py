"""Read-only HTML source locator for Live selections without stable selectors."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from html import unescape
from pathlib import Path

VOID = set('area base br col embed hr img input link meta param source track wbr'.split())


class LocatorError(ValueError):
    pass


class Tree(HTMLParser):
    CDATA_CONTENT_ELEMENTS = ('script', 'style', 'textarea', 'title')
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.lines = [0] + [m.end() for m in re.finditer('\n', source)]
        self.nodes, self.stack = [], []
        self.feed(source)
        self.close()
        if self.stack:
            raise LocatorError('unclosed_markup')

    def source_offset(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self.source_offset()
        node = dict(tag=tag, attrs=sorted(attrs), start=start,
                    end=start + len(self.get_starttag_text()), children=[], parent=self.stack[-1] if self.stack else None)
        if self.stack:
            self.stack[-1]['children'].append(node)
        self.nodes.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        if tag not in VOID:
            raise LocatorError('unsupported_self_closing_html')
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1]['tag'] != tag:
            raise LocatorError('unsupported_or_mismatched_markup')
        node = self.stack.pop()
        node['end'] = self.source.index('>', self.source_offset()) + 1

    def handle_data(self, data):
        if self.stack:
            if self.stack[-1]['tag'] in ('textarea', 'title'):
                data = unescape(data)
            self.stack[-1]['children'].append(data)


def signature(node):
    # Merge adjacent text tokens so entity encoding and comments do not change identity.
    parts = []
    for child in node['children']:
        if isinstance(child, str):
            if parts and isinstance(parts[-1], str):
                parts[-1] += child
            else:
                parts.append(child)
        else:
            parts.append(signature(child))
    return (node['tag'], node['attrs'], [re.sub(r'\s+', ' ', x) if isinstance(x, str) else x for x in parts])


def locate(source, event):
    expected = Tree(event['element']['outerHTML'])
    roots = [n for n in expected.nodes if n['parent'] is None]
    if len(roots) != 1 or roots[0]['tag'] != event['element']['tagName'].lower():
        raise LocatorError('invalid_element')
    tree = Tree(source)
    target = signature(roots[0])
    matches = [n for n in tree.nodes if signature(n) == target]
    # A supplied parent id/class may narrow identical siblings in separate regions.
    context = event['element'].get('parentContext', '')
    hint = HTMLParser()
    parents = []
    hint.handle_starttag = lambda tag, attrs: parents.append((tag, dict(attrs)))
    hint.feed(context)
    if parents:
        tag, attrs = parents[0]
        anchors = {k: v for k, v in attrs.items() if k in ('id', 'class')}
        if anchors:
            matches = [n for n in matches if n['parent'] and n['parent']['tag'] == tag
                       and all(dict(n['parent']['attrs']).get(k) == v for k, v in anchors.items())]
    if len(matches) != 1:
        raise LocatorError('element_ambiguous' if matches else 'element_not_found')
    node = matches[0]
    return node['start'], node['end']


def scaffold(source, event):
    session = event['id']
    count = event.get('count', 3)
    if not re.fullmatch(r'[a-f0-9]{8}', session) or type(count) is not int or not 1 <= count <= 8:
        raise LocatorError('invalid_session')
    block_tags = set('address article aside blockquote div dl fieldset figure figcaption footer form h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section table ul'.split())
    display = event['element'].get('computedStyles', {}).get('display', '')
    if event['element']['tagName'].lower() not in block_tags or display.startswith('inline'):
        raise LocatorError('inline_source_requires_framework_locator')
    start, end = locate(source, event)
    original = source[start:end]
    wrapper = (f'\n<!-- impeccable-variants-start {session} -->\n'
               f'<div data-impeccable-variants="{session}" data-impeccable-variant-count="{count}" style="display: contents">\n'
               f'<div data-impeccable-variant="original">{original}</div>\n'
               '<!-- Variants: insert below this line -->\n</div>\n'
               f'<!-- impeccable-variants-end {session} -->\n')
    return dict(ok=True, sourceWritten=False, replaceStartOffset=start, replaceEndOffset=end,
                original=original, wrapperBlock=wrapper,
                sourceSha256=hashlib.sha256(source.encode('utf-8')).hexdigest(),
                offsetUnit='Python Unicode characters', styleMode='scoped',
                styleTag=f'<style data-impeccable-css="{session}">')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--event', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.file.is_symlink() or args.file.suffix.lower() not in ('.html', '.htm'):
            raise LocatorError('unsupported_source')
        # Preserve CRLF and Unicode exactly: offsets address this decoded byte sequence.
        source = args.file.read_bytes().decode('utf-8')
        result = scaffold(source, json.loads(args.event.read_text(encoding='utf-8-sig')))
        result['file'] = str(args.file)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps(dict(ok=False, error=str(error), sourceWritten=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
