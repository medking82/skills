"""Read-only HTML source locator for Live selections without stable selectors."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import os
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
    selection = event.get('sourceLocator')
    if selection:
        bodies = [n for n in tree.nodes if n['tag'] == 'body']
        if len(bodies) != 1:
            raise LocatorError('source_body_not_unique')
        picked = bodies[0]
        for step in selection['path']:
            children = [n for n in picked['children'] if isinstance(n, dict)]
            index = step['index']
            if type(index) is not int or not 0 <= index < len(children):
                raise LocatorError('dom_source_path_mismatch')
            picked = children[index]
            if picked['tag'] != step['tag']:
                raise LocatorError('dom_source_path_mismatch')
        parent_tree = Tree(selection['parentHTML'])
        parent_roots = [n for n in parent_tree.nodes if n['parent'] is None]
        if (len(parent_roots) != 1 or not picked['parent']
                or signature(picked['parent']) != signature(parent_roots[0])):
            raise LocatorError('dom_source_parent_mismatch')
        matches = [n for n in matches if n is picked]
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


def scaffold(source, event, detached=False):
    session = event['id']
    count = event.get('count', 3)
    if not re.fullmatch(r'[a-f0-9]{8}', session) or type(count) is not int or not 1 <= count <= 8:
        raise LocatorError('invalid_session')
    if event['element']['tagName'].lower() in set('html head body script style textarea title select option optgroup table caption colgroup tbody thead tfoot tr td th svg math'.split()):
        raise LocatorError('unsupported_preview_context')
    block_tags = set('address article aside blockquote div dl fieldset figure figcaption footer form h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section table ul'.split())
    display = event['element'].get('computedStyles', {}).get('display', '')
    detached = detached or event['element']['tagName'].lower() not in block_tags or display.startswith('inline')
    start, end = locate(source, event)
    original = source[start:end]
    wrapper = (f'\n<!-- impeccable-variants-start {session} -->\n'
               f'<div data-impeccable-variants="{session}" data-impeccable-variant-count="{count}" style="display: contents">\n'
               f'<div data-impeccable-variant="original">{original}</div>\n'
               '<!-- Variants: insert below this line -->\n</div>\n'
               f'<!-- impeccable-variants-end {session} -->\n')
    if detached:
        # Compact span shells introduce neither whitespace text nodes nor block boxes.
        wrapper = (f'<!-- impeccable-variants-start {session} -->'
                   f'<span data-impeccable-variants="{session}" data-impeccable-variant-count="{count}" style="display:contents">'
                   f'<style data-impeccable-css="{session}">span[data-impeccable-variants="{session}"]>span[data-impeccable-variant]{{display:contents!important}}</style>'
                   f'<span data-impeccable-variant="original" style="display:contents">{original}</span>'
                   '<!-- Variants: insert below this line --></span>'
                   f'<!-- impeccable-variants-end {session} -->')
    return dict(ok=True, sourceWritten=False, replaceStartOffset=start, replaceEndOffset=end,
                original=original, wrapperBlock=wrapper,
                publishToSource=not detached, sessionId=session,
                sourceSha256=hashlib.sha256(source.encode('utf-8')).hexdigest(),
                offsetUnit='Python Unicode characters', styleMode='scoped',
                styleTag=f'<style data-impeccable-css="{session}">')


def apply_selection(path, receipt, replacement, session_id=None, template_approval=None):
    """Commit one accepted detached variant; refuse any source drift before writing."""
    if receipt.get('publishToSource') is not False or path.is_symlink():
        raise LocatorError('not_a_detached_receipt')
    if not session_id or session_id != receipt.get('sessionId'):
        raise LocatorError('session_mismatch')
    if not receipt.get('file') or Path(receipt['file']).resolve() != path.resolve():
        raise LocatorError('receipt_file_mismatch')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt['sourceSha256']:
        raise LocatorError('source_changed')
    source = raw.decode('utf-8')
    start, end = receipt['replaceStartOffset'], receipt['replaceEndOffset']
    if source[start:end] != receipt['original']:
        raise LocatorError('source_range_mismatch')
    if receipt.get('sourceKind') == 'jsx':
        if (path.suffix.lower() not in ('.jsx', '.tsx') or not template_approval
                or template_approval.get('ok') is not True
                or template_approval.get('validator') not in ('babel-jsx-static-edits-v1', 'babel-jsx-structural-edits-v1')
                or template_approval.get('receipt') != receipt
                or template_approval.get('replacementSha256') != hashlib.sha256(replacement.encode('utf-8')).hexdigest()):
            raise LocatorError('missing_or_mismatched_template_validation')
    else:
        parsed = Tree(replacement)
        roots = [n for n in parsed.nodes if n['parent'] is None]
        original = Tree(receipt['original']).nodes[0]
        if len(roots) != 1 or roots[0]['tag'] != original['tag'] or replacement[roots[0]['start']:roots[0]['end']] != replacement:
            raise LocatorError('replacement_must_be_one_matching_element')
        if any(k.startswith(('data-impeccable-', 'data-p-')) for n in parsed.nodes for k, _ in n['attrs']):
            raise LocatorError('replacement_has_live_markers')
    desired = (source[:start] + replacement + source[end:]).encode('utf-8')
    # Preserve the existing file object/permissions. Opening r+b does not truncate.
    with path.open('r+b') as handle:
        if os.name == 'nt':
            import msvcrt
            length = max(len(raw), len(desired), 1)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, length)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if handle.read() != raw:
                raise LocatorError('source_changed')
            handle.seek(0)
            handle.write(desired)
            handle.truncate()
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, length)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)
    return dict(ok=True, sourceWritten=True, sha256=hashlib.sha256(desired).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--event', type=Path)
    parser.add_argument('--detached', action='store_true')
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--replacement', type=Path)
    parser.add_argument('--session-id')
    parser.add_argument('--template-approval', type=Path)
    args = parser.parse_args()
    try:
        allowed = ('.html', '.htm', '.jsx', '.tsx') if args.template_approval else ('.html', '.htm')
        if args.file.is_symlink() or args.file.suffix.lower() not in allowed:
            raise LocatorError('unsupported_source')
        # Preserve CRLF and Unicode exactly: offsets address this decoded byte sequence.
        source = args.file.read_bytes().decode('utf-8')
        if args.receipt and args.replacement:
            result = apply_selection(args.file, json.loads(args.receipt.read_text(encoding='utf-8-sig')),
                                     args.replacement.read_bytes().decode('utf-8'), args.session_id,
                                     json.loads(args.template_approval.read_text(encoding='utf-8-sig')) if args.template_approval else None)
        elif args.event:
            result = scaffold(source, json.loads(args.event.read_text(encoding='utf-8-sig')), args.detached)
        else:
            raise LocatorError('event_or_receipt_and_replacement_required')
        result['file'] = str(args.file)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps(dict(ok=False, error=str(error), sourceWritten=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
