const test = require('node:test');
const assert = require('node:assert/strict');
const { createRequire } = require('node:module');

// Exercise the actual transitive resolution, not a test-only implementation.
const fromPreferences = createRequire(require.resolve('puppeteer-extra-plugin-user-preferences'));
const merge = fromPreferences('deepmerge');
const poison = () => JSON.parse('{"__proto__":{"injected":true},"constructor":{"prototype":{"injected":true}},"prototype":{"injected":true},"safe":{"value":1}}');

test('transitive resolution and lock point only to the reviewed local fork', () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const root = path.join(__dirname, '..');
  assert.equal(fromPreferences.resolve('deepmerge'), path.join(root, 'vendor/deepmerge-hardened/index.cjs'));
  assert.equal(fromPreferences('deepmerge/package.json').name, '@sprut/deepmerge-hardened');
  const lock = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json'), 'utf8'));
  const entries = Object.entries(lock.packages).filter(([key]) => key.endsWith('/deepmerge'));
  assert.deepEqual(entries, [['node_modules/deepmerge', { resolved: 'vendor/deepmerge-hardened', link: true }]]);
  assert.deepEqual(lock.packages['vendor/deepmerge-hardened'].engines, { node: '>=24 <25' });
});

function assertClean(value) {
  assert.equal(Object.getPrototypeOf(value), Object.prototype);
  assert.equal(value.injected, undefined);
  for (const key of ['__proto__', 'constructor', 'prototype']) {
    assert.equal(Object.hasOwn(value, key), false, key);
  }
  assert.equal({}.injected, undefined);
}

for (const [name, makeTarget, makeSource] of [
  ['target cloning', poison, () => ({})],
  ['source with null-prototype target', () => Object.create(null), poison],
  ['source with target own __proto__', poison, poison],
  ['ordinary source', () => ({}), poison],
]) {
  test(`merge rejects prototype-control keys during ${name}`, () => {
    const result = merge(makeTarget(), makeSource());
    assertClean(result);
    assert.deepEqual(result.safe, { value: 1 });
  });
}

test('nested target/source and array elements are hardened, without input mutation', () => {
  const target = { nested: poison(), list: [poison()] };
  const source = { nested: poison(), list: [poison()] };
  const before = JSON.stringify([target, source]);
  const result = merge(target, source);
  assertClean(result.nested);
  assert.equal(result.list.length, 2);
  result.list.forEach(assertClean);
  assert.equal(JSON.stringify([target, source]), before);
  assert.notEqual(result.list[0], target.list[0]);
});

test('blocked getters are never read and cannot reach customMerge', () => {
  const bad = { safe: 1 };
  for (const key of ['__proto__', 'constructor', 'prototype']) {
    Object.defineProperty(bad, key, { enumerable: true, get() { throw new Error('blocked getter'); } });
  }
  const result = merge(bad, bad, { customMerge(key) {
    assert.ok(!['__proto__', 'constructor', 'prototype'].includes(key));
  } });
  assertClean(result);
  assert.equal(result.safe, 1);
});

test('all, clone:false and custom array cloning retain the security boundary', () => {
  assertClean(merge.all([poison(), poison()]));
  assertClean(merge(poison(), poison(), { clone: false }));
  const result = merge([poison()], [poison()], {
    arrayMerge(target, source, options) {
      return target.concat(source).map(value => options.cloneUnlessOtherwiseSpecified(value, options));
    },
  });
  result.forEach(assertClean);
});

test('normal preference merging preserves recursive precedence, arrays, cloning and all', () => {
  const user = { webkit: { webprefs: { font: 22, enabled: false } }, languages: ['en'] };
  const plugin = { webkit: { webprefs: { enabled: true } }, languages: ['fr'] };
  const expected = { webkit: { webprefs: { font: 22, enabled: true } }, languages: ['en', 'fr'] };
  assert.deepEqual(merge(user, plugin), expected);
  assert.deepEqual(merge.all([user, plugin]), expected);
  assert.deepEqual(merge.all([]), {});
  assert.throws(() => merge.all({}), /first argument should be an array/);
  const result = merge(user, plugin);
  result.webkit.webprefs.font = 99;
  result.languages.push('de');
  assert.equal(user.webkit.webprefs.font, 22);
  assert.deepEqual(user.languages, ['en']);
  assert.deepEqual(merge({ list: [1] }, { list: { value: 2 } }), { list: { value: 2 } });
  assert.deepEqual(merge({ list: {} }, { list: [1] }), { list: [1] });
});

test('merge options, enumerable symbols, special objects and inherited guards stay compatible', () => {
  const symbol = Symbol('preference');
  const date = new Date(0);
  const regexp = /fixture/;
  const react = { $$typeof: Symbol.for('react.element'), props: {} };
  const input = { child: { value: 1 }, date, regexp, react, [symbol]: { value: 2 } };
  const cloned = merge({}, input);
  assert.notEqual(cloned.child, input.child);
  assert.notEqual(cloned[symbol], input[symbol]);
  assert.equal(cloned.date, date);
  assert.equal(cloned.regexp, regexp);
  assert.equal(cloned.react, react);
  assert.equal(merge({}, input, { clone: false }).child, input.child);
  assert.deepEqual(merge({ list: [1] }, { list: [2] }, { arrayMerge: (_a, b) => b }), { list: [2] });
  assert.deepEqual(merge({ child: { a: 1 } }, { child: { b: 2 } }, {
    customMerge: key => key === 'child' ? (a, b) => ({ sum: a.a + b.b }) : undefined,
  }), { child: { sum: 3 } });
  class Special { constructor() { this.value = 3; } }
  const instance = new Special();
  assert.equal(merge({}, { instance }, {
    isMergeableObject: value => value !== null && typeof value === 'object' && !(value instanceof Special),
  }).instance, instance);
  assert.deepEqual(merge(Object.create({ inherited: 1 }), { inherited: 2, own: 3 }), { own: 3 });
  assert.deepEqual(merge({}, { toString: 'not a function' }), {});
});

test('real user-preferences lifecycle preserves plugin contributions and serialized profile data', async () => {
  const preferences = require('puppeteer-extra-plugin-user-preferences')({
    userPrefs: { profile: { enabled: false }, languages: ['en'], nested: poison() },
  });
  assert.equal(preferences.name, 'user-preferences');
  assert.deepEqual([...preferences.requirements], ['runLast', 'dataFromPlugins']);
  assert.deepEqual([...preferences.dependencies], ['user-data-dir']);
  preferences.getDataFromPlugins = name => {
    assert.equal(name, 'userPreferences');
    return [{ value: { profile: { enabled: true }, languages: ['fr'] } }, { value: { nested: poison() } }];
  };
  const options = { headless: true };
  await preferences.beforeLaunch(options);
  assert.deepEqual(options, { headless: true });
  assertClean(preferences.combinedPrefs.nested);
  assert.deepEqual(preferences.combinedPrefs.languages, ['en', 'fr']);
  assert.deepEqual(preferences.combinedPrefs.profile, { enabled: true });
  const [data] = preferences.data;
  assert.equal(data.name, 'userDataDirFile');
  assert.equal(data.value.target, 'Profile');
  assert.equal(data.value.file, 'Preferences');
  assert.deepEqual(JSON.parse(data.value.contents), preferences.combinedPrefs);
  // Never launch a browser, create a real profile or connect to a provider.
});

test('real plugin manager resolves, orders and dispatches preferences into a synthetic profile', async () => {
  const fs = require('node:fs');
  const os = require('node:os');
  const path = require('node:path');
  const { PluginList } = require('playwright-extra');
  const { PuppeteerExtraPlugin } = require('puppeteer-extra-plugin');
  class Contributor extends PuppeteerExtraPlugin {
    get name() { return 'synthetic-preferences-contributor'; }
    get data() { return [{ name: 'userPreferences', value: { languages: ['fr'], nested: poison() } }]; }
  }
  const plugins = new PluginList();
  plugins.onPluginError = (_plugin, _method, error) => { throw error; };
  plugins.setDependencyDefaults('user-preferences', { userPrefs: { languages: ['en'], nested: poison() } });
  plugins.add(require('puppeteer-extra-plugin-stealth')());
  plugins.add(new Contributor());
  plugins.prepare();
  const names = plugins.names;
  assert.ok(names.includes('user-preferences'));
  assert.ok(names.indexOf('user-preferences') < names.indexOf('user-data-dir'));
  assert.ok(names.indexOf('synthetic-preferences-contributor') < names.indexOf('user-preferences'));
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'synthetic-preference-test-'));
  try {
    // Only pre-launch hooks: no browser, HTTP listener, auth or provider call.
    const options = { userDataDir: directory, args: [], headless: true };
    await plugins.dispatchBlocking('beforeLaunch', options);
    const saved = JSON.parse(fs.readFileSync(path.join(directory, 'Default/Preferences'), 'utf8'));
    assert.deepEqual(saved.languages, ['en', 'fr']);
    assertClean(saved.nested);
    const preferences = plugins.list.find(p => p.name === 'user-preferences');
    assert.deepEqual(saved, preferences.combinedPrefs);
    assert.equal(options.userDataDir, directory);
    await plugins.dispatchBlocking('onDisconnected');
    assert.equal(fs.existsSync(directory), true); // Existing profiles are not deleted by default.
  } finally {
    fs.rmSync(directory, { recursive: true, force: true }); // Only this test-created fixture.
  }
});
