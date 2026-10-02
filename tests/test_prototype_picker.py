from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PICKER = REPO_ROOT / "skills" / "prototype" / "PICKER.md"
NODE = shutil.which("node")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Execute the documented wiring against a small DOM adapter. Assertions inspect
# observable selection, rendering, history, and event cancellation, not wording.
HARNESS = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = SOURCE;

function open(search) {
  const keys = {};
  const stage = { innerHTML: '' };
  const highlight = { style: {} };
  const items = Array.from({ length: 3 }, (_, i) => ({
    offsetWidth: 50, offsetLeft: i * 50, attributes: {}, listeners: {},
    toggleAttribute(key, on) { if (on) this.attributes[key] = ''; else delete this.attributes[key]; },
    setAttribute(key, value) { this.attributes[key] = value; },
    removeAttribute(key) { delete this.attributes[key]; },
    addEventListener(key, fn) { this.listeners[key] = fn; },
  }));
  const replay = { addEventListener(key, fn) { this[key] = fn; } };
  const picker = {
    querySelector(selector) { return selector.includes('highlight') ? highlight : replay; },
    querySelectorAll() { return items; },
    setAttribute() {},
  };
  let renders = 0;
  let url = 'https://example.test/prototype' + search;
  const context = {
    document: {
      getElementById() { return stage; }, querySelector() { return picker; },
      addEventListener(key, fn) { keys[key] = fn; },
    },
    window: { addEventListener() {} },
    location: { search, toString() { return url; } },
    history: { replaceState(_state, _unused, next) { url = String(next); } },
    variants: [0, 1, 2].map(i => () => { renders++; return 'variant-' + i; }),
    requestAnimationFrame(fn) { fn(); }, URL, URLSearchParams,
  };
  vm.runInNewContext(source, context);
  return {
    stage, items, replay,
    renders() { return renders; },
    selected() { return items.findIndex(item => item.attributes['aria-current'] === 'true'); },
    url() { return new URL(url); },
    press(key, props = {}, target = {}) {
      const event = {
        key, target: { tagName: 'DIV', isContentEditable: false, ...target },
        prevented: false, preventDefault() { this.prevented = true; }, ...props,
      };
      keys.keydown(event);
      return event;
    },
  };
}

for (const query of ['', '?v=0', '?v=-1', '?v=4', '?v=999', '?v=1.5', '?v=2junk',
  '?v=NaN', '?v=Infinity', '?v=', '?v=9007199254740993']) {
  const page = open(query);
  assert.equal(page.selected(), 0, query);
  assert.equal(page.stage.innerHTML, 'variant-0', query);
  assert.equal(page.url().searchParams.get('v'), '1', query);
}
for (const value of [1, 2, 3]) {
  const page = open('?v=' + value);
  assert.equal(page.selected(), value - 1);
  assert.equal(page.stage.innerHTML, 'variant-' + (value - 1));
}
const page = open('?v=3');
assert.equal(page.press('ArrowRight').prevented, true);
assert.equal(page.selected(), 0);
assert.equal(page.press('ArrowLeft').prevented, true);
assert.equal(page.selected(), 2);
assert.equal(page.press('2').prevented, true);
assert.equal(page.selected(), 1);
assert.equal(page.url().searchParams.get('v'), '2');
assert.equal(page.press('4').prevented, false);
assert.equal(page.press('z').prevented, false);
for (const modifier of ['metaKey', 'ctrlKey', 'altKey', 'shiftKey']) {
  assert.equal(page.press('ArrowRight', { [modifier]: true }).prevented, false);
  assert.equal(page.selected(), 1);
}
for (const tagName of ['INPUT', 'TEXTAREA', 'SELECT']) {
  assert.equal(page.press('ArrowRight', {}, { tagName }).prevented, false);
  assert.equal(page.selected(), 1);
}
assert.equal(page.press('ArrowRight', {}, { isContentEditable: true }).prevented, false);
const beforeReplay = page.renders();
assert.equal(page.press('r').prevented, true);
assert.equal(page.renders(), beforeReplay + 1);
assert.equal(page.selected(), 1);
page.items[2].listeners.click();
assert.equal(page.selected(), 2);
assert.equal(page.stage.innerHTML, 'variant-2');
page.replay.click();
assert.equal(page.renders(), beforeReplay + 3);
assert.equal(page.items.filter(item => item.attributes['aria-current'] === 'true').length, 1);
"""


@unittest.skipUnless(NODE, "Node.js is needed to execute the picker reference")
class PrototypePickerTests(unittest.TestCase):
    def test_documented_picker_behavior(self) -> None:
        blocks = re.findall(r"```js\n(.*?)\n```", PICKER.read_text(encoding="utf-8"), re.S)
        self.assertEqual(len(blocks), 1, "expected one executable reference wiring block")
        result = subprocess.run(
            [NODE, "-e", HARNESS.replace("SOURCE", json.dumps(blocks[0]), 1)],
            capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL,
            creationflags=NO_WINDOW,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
