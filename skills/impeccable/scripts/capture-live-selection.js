// Install as a browser init script BEFORE Live initializes. Never alter page nodes.
(() => {
  if (window.__DESIGN_LIVE_SELECTION__) return;
  if (window.__IMPECCABLE_LIVE_INIT__) throw new Error('Install capture before Live; reload with an init script');
  const records = new Map();
  let active = true;
  let module = window.__IMPECCABLE_LIVE_DOM__;
  function pathFor(el) {
    const path = [];
    for (let node = el; node && node !== document.body; node = node.parentElement) {
      if (!node.parentElement) return null;
      path.unshift({tag: node.tagName.toLowerCase(), index: [...node.parentElement.children].indexOf(node)});
    }
    return path;
  }
  function wrap(value) {
    if (!value?.createLiveBrowserDomHelpers) return value;
    const factory = value.createLiveBrowserDomHelpers;
    value.createLiveBrowserDomHelpers = function (...args) {
      const helpers = factory.apply(this, args);
      const clone = helpers.cloneWithoutChrome;
      helpers.cloneWithoutChrome = function (el) {
        const result = clone.call(this, el);
        const id = window.__IMPECCABLE_LIVE_CHROME_CORE__?.debugState().currentSessionId;
        if (active && id && !records.has(id) && el.parentElement && result.outerHTML.length <= 10000) {
          records.set(id, {outerHTML: result.outerHTML, path: pathFor(el), parentHTML: el.parentElement.outerHTML});
          if (records.size > 32) records.delete(records.keys().next().value);
        }
        return result;
      };
      return helpers;
    };
    return value;
  }
  if (module) module = wrap(module);
  Object.defineProperty(window, '__IMPECCABLE_LIVE_DOM__', {
    configurable: true, get: () => module, set: value => { module = wrap(value); }
  });
  window.__DESIGN_LIVE_SELECTION__ = {
    forEvent(event) {
      const match = records.get(event.id);
      if (!match?.path || match.outerHTML !== event.element.outerHTML) throw new Error('No matching session snapshot; capture again');
      return {path: match.path, parentHTML: match.parentHTML};
    },
    dispose() {
      active = false;
      records.clear();
      Object.defineProperty(window, '__IMPECCABLE_LIVE_DOM__', {configurable: true, writable: true, value: module});
      delete window.__DESIGN_LIVE_SELECTION__;
    }
  };
})();
