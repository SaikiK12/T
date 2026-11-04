/* Adapter for verified, static export bundles. No native data scan or job execution. */
(() => {
  'use strict';
  const ids = /^[a-z][a-z0-9_]{0,63}$/;
  const raw = new Map(), calculations = new Map(), cache = new Map(), listeners = new Set();
  let config, started = false, completion;
  const banner = (state, message) => {
    const node = document.getElementById('standalone-status');
    if (node) { node.dataset.state = state; node.textContent = message; }
  };
  const fail = (code, detail) => Object.freeze({status: 'error', error: code, detail});
  const freeze = (value) => {
    if (value && typeof value === 'object' && !Object.isFrozen(value)) {
      Object.values(value).forEach(freeze); Object.freeze(value);
    }
    return value;
  };
  const rows = (value) => {
    if (!Array.isArray(value) || value.some(row => !row || typeof row !== 'object' || Array.isArray(row))) {
      throw new Error('row_object_array_required');
    }
    const stack = [[value, 0]];
    while (stack.length) {
      const [item, depth] = stack.pop();
      if (depth > 64) throw new Error('nesting_bound');
      if (typeof item === 'number' && !Number.isFinite(item)) throw new Error('nonfinite_calculation');
      if (item && typeof item === 'object') Object.values(item).forEach(x => stack.push([x, depth + 1]));
    }
    return freeze(value);
  };
  const notify = () => {
    for (const fn of listeners) {
      try { fn(); } catch (_) { banner('error', 'Static snapshot: page render failed; displayed state is incomplete.'); }
    }
  };
  const evaluate = (id, visiting = new Set()) => {
    if (raw.has(id)) return raw.get(id);
    if (cache.has(id)) return cache.get(id);
    if (!calculations.has(id)) return Object.freeze({status: 'missing', error: 'undeclared_dataset'});
    if (visiting.has(id)) return fail('dependency_cycle', id);
    const next = new Set(visiting); next.add(id);
    const calculation = calculations.get(id), inputs = calculation.inputs.map(dep => evaluate(dep, next));
    let state;
    const bad = inputs.findIndex(x => x.status !== 'ok' && x.status !== 'loading');
    if (bad >= 0) state = fail('dependency_failed', calculation.inputs[bad]);
    else if (inputs.some(x => x.status === 'loading')) state = Object.freeze({status: 'loading'});
    else {
      try { state = Object.freeze({status: 'ok', data: rows(calculation.fn(...inputs.map(x => x.data)))}); }
      catch (_) { state = fail('calculation_failed', id); }
    }
    cache.set(id, state); return state;
  };
  try {
    config = JSON.parse(document.getElementById('standalone-config').textContent);
    if (config.version !== 1 || !/^[a-f0-9]{64}$/.test(config.generation) || !config.datasets) throw new Error();
    for (const id of Object.keys(config.datasets)) {
      if (!ids.test(id)) throw new Error();
      raw.set(id, Object.freeze({status: 'loading'}));
    }
  } catch (_) {
    config = null; banner('error', 'Static snapshot: invalid adapter configuration.');
  }
  const load = async (id, item) => {
    if (!ids.test(id) || item.file !== `data/${id}.json` || !/^[a-f0-9]{64}$/.test(item.sha256) ||
        !Number.isSafeInteger(item.bytes) || item.bytes < 0 || item.bytes > config.max_dataset_bytes ||
        !Number.isSafeInteger(item.rows) || item.rows < 0) throw new Error('invalid_dataset_declaration');
    if (!globalThis.crypto || !crypto.subtle) throw new Error('webcrypto_requires_https_or_localhost');
    const response = await fetch(item.file, {cache: 'no-store', credentials: 'omit', redirect: 'error'});
    if (!response.ok || !response.body) throw new Error('dataset_unavailable');
    const reader = response.body.getReader(), chunks = []; let size = 0;
    try {
      while (true) {
        const {done, value} = await reader.read(); if (done) break;
        size += value.byteLength;
        if (size > item.bytes) throw new Error('dataset_size_mismatch');
        chunks.push(value);
      }
    } catch (error) { await reader.cancel(); throw error; }
    if (size !== item.bytes) throw new Error('dataset_size_mismatch');
    const bytes = new Uint8Array(size); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
    if (digest !== item.sha256) throw new Error('dataset_hash_mismatch');
    const value = rows(JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes)));
    if (value.length !== item.rows) throw new Error('dataset_row_count_mismatch');
    return Object.freeze({status: 'ok', data: value});
  };
  window.dash = Object.freeze({
    colors: Object.freeze(['#2864ba', '#0b887c', '#a95f0b', '#8054ad', '#b44f6b', '#56737e']),
    calc(id, calculation) {
      if (!ids.test(id) || raw.has(id) || calculations.has(id) || !calculation ||
          !Array.isArray(calculation.inputs) || calculation.inputs.some(x => !ids.test(x)) ||
          typeof calculation.fn !== 'function') throw new Error('invalid_or_duplicate_calculation');
      calculations.set(id, Object.freeze({inputs: Object.freeze([...calculation.inputs]), fn: calculation.fn})); cache.clear();
    },
    data: id => evaluate(id),
    onData(fn) {
      if (typeof fn !== 'function') throw new Error('callback_required');
      listeners.add(fn); queueMicrotask(() => { if (listeners.has(fn)) notify(); });
      return () => listeners.delete(fn);
    },
    setLink(name) {
      if (!/^[a-z][a-z0-9_-]*$/.test(name)) throw new Error('invalid_tab_link');
      history.replaceState(null, '', `#${name}`);
    },
    start() {
      if (started) return completion; started = true;
      completion = (async () => {
        if (!config) { notify(); return; }
        if (!window.d3 || typeof d3.format !== 'function') {
          for (const id of raw.keys()) raw.set(id, fail('d3_dependency_missing'));
          cache.clear(); banner('error', 'Static snapshot: pinned D3 dependency failed to load.'); notify(); return;
        }
        const all = Object.entries(config.datasets).sort(([a], [b]) => a.localeCompare(b));
        if (all.reduce((sum, [, item]) => sum + item.bytes, 0) > config.max_total_bytes) {
          for (const id of raw.keys()) raw.set(id, fail('dataset_budget_exceeded'));
        } else {
          await Promise.all(all.map(async ([id, item]) => {
            try { raw.set(id, await load(id, item)); }
            catch (error) { raw.set(id, fail(String(error.message || error), id)); }
          }));
        }
        cache.clear();
        const errors = [...raw.values()].filter(value => value.status !== 'ok').length;
        banner(errors ? 'error' : 'ok', errors ?
          `Static snapshot: ${errors} dataset(s) failed verification; unknown values are not zero.` :
          `Static snapshot exported ${config.generated_at}; generation ${config.generation}. No live refresh or job execution.`);
        notify();
      })();
      return completion;
    },
  });
})();
