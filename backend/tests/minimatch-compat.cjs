const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createRequire } = require('node:module');
const { promisify } = require('node:util');
const { spawnSync } = require('node:child_process');
const legacy = require('minimatch');

const from = name => createRequire(require.resolve(name));
function fixture(t) {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'minimatch-fixture-')));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  return dir;
}
function write(root, name, content = '') {
  const file = path.join(root, name);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
  return file;
}

// Also exercised against the old engine by the bounded negative-control runner.
const amplificationProbe = `
  const assert = require('node:assert/strict');
  const { Minimatch } = require(process.argv[1]);
  const mm = new Minimatch('a', { optimizationLevel: 2, braceExpandMax: 2 });
  const parts = mm.firstPhasePreProcess(['a/**/../b/**/../c/**/../d/**/../e'.split('/')]);
  assert.ok(parts.length <= 2, 'first phase must honor the expansion budget');
  let comparisons = 0;
  mm.partsMatch = () => { comparisons++; return false; };
  const rows = Array.from({ length: 1001 }, (_, i) => [String(i)]);
  mm.secondPhasePreProcess(rows);
  assert.equal(comparisons, 0, 'large sets must skip pairwise comparisons');
`;

test('all reviewed consumers resolve the intended fixed engine or callable adapter', () => {
  for (const name of ['eslint', '@eslint/eslintrc', '@humanwhocodes/config-array', 'glob']) {
    const resolved = from(name)('minimatch');
    assert.equal(resolved, legacy, name);
    assert.equal(typeof resolved, 'function');
    assert.equal(from(name)('minimatch/package.json').name, '@sprut/minimatch-compat');
  }
  for (const name of ['nodemon', '@typescript-eslint/typescript-estree']) {
    const consumer = from(name);
    assert.equal(consumer('minimatch/package.json').version, '11.0.4');
    assert.equal(typeof consumer('minimatch').minimatch, 'function');
  }
  const engine = require('minimatch-engine/package.json');
  assert.equal(engine.name, 'minimatch'); // npm alias, not renamed vulnerable source.
  assert.equal(engine.version, '11.0.4');
  const lock = require('../package-lock.json');
  for (const [location, pkg] of Object.entries(lock.packages)) {
    if (location.endsWith('/minimatch') || location.endsWith('/minimatch-engine')) {
      if (pkg.link) assert.equal(pkg.resolved, 'vendor/minimatch-compat');
      else {
        assert.equal(pkg.version, '11.0.4', location);
        assert.equal(pkg.resolved, 'https://registry.npmjs.org/minimatch/-/minimatch-11.0.4.tgz');
        assert.ok(pkg.integrity.startsWith('sha512-'));
      }
    }
  }
});

test('callable legacy API: match, constructor, defaults, helpers and negative controls', () => {
  const unadapted = require('minimatch-engine');
  assert.throws(() => unadapted('a.ts', '*.ts'), TypeError);
  assert.equal(legacy('src/a.ts', '**/*.ts'), true);
  assert.equal(legacy('src/a.js', '**/*.ts'), false);
  assert.equal(legacy('src/.a.ts', '**/*.ts'), false);
  assert.equal(legacy('src/.a.ts', '**/*.ts', { dot: true }), true);
  assert.equal(legacy('a.ts', '  *.ts  '), true);
  assert.equal(legacy('a.ts', '!*.js'), true);
  assert.equal(legacy('a.js', '!*.js'), false);
  assert.equal(legacy('#a', '#*'), false);
  assert.equal(legacy('#a', '#*', { nocomment: true }), true);
  assert.throws(() => legacy('a', null), TypeError);
  assert.throws(() => legacy('a', '*'.repeat(65537)), TypeError);
  assert.throws(() => legacy('a', ' '.repeat(65536) + '*'), TypeError);
  assert.equal(legacy.Minimatch('*.ts').match('a.ts'), true);
  assert.equal(new legacy.Minimatch('*.ts').match('a.js'), false);
  assert.equal(new legacy.Minimatch('**/*.ts').set[0][0], legacy.GLOBSTAR);
  const defaults = legacy.defaults({ dot: true, nocase: true });
  assert.equal(defaults('.A.TS', '*.ts'), true);
  assert.equal(defaults('.A.TS', '*.ts', { dot: false }), false);
  assert.equal(defaults.Minimatch.defaults({ nocase: false })('*.ts').match('.A.TS'), false);
  assert.deepEqual(['a.ts', 'b.js'].filter(legacy.filter('*.ts')), ['a.ts']);
  assert.deepEqual(legacy.braceExpand('*.{js,ts}'), ['*.js', '*.ts']);
  assert.deepEqual(legacy.match(['a.ts', 'b.js'], '*.ts'), ['a.ts']);
  assert.deepEqual(legacy.match([], '*.ts', { nonull: true }), ['*.ts']);
});

test('upstream fixed preprocessing has bounded amplification, even with optimization level 2', () => {
  for (const entry of [require.resolve('minimatch-engine'), from('nodemon').resolve('minimatch')]) {
    const child = spawnSync(process.execPath, ['--max-old-space-size=128', '-e', amplificationProbe, entry], {
      encoding: 'utf8', timeout: 5000,
    });
    assert.ifError(child.error);
    assert.equal(child.status, 0, child.stderr);
  }
  assert.equal(legacy('src/a.ts', '**/*.{js,ts}', { optimizationLevel: 2 }), true);
  assert.equal(legacy('src/a.py', '**/*.{js,ts}', { optimizationLevel: 2 }), false);
});

test('actual glob 7 async/sync matching retains dot, brace, extglob, ignore and nonull behavior', async t => {
  const root = fixture(t);
  for (const name of ['src/a.ts', 'src/b.js', 'src/nested/c.ts', 'src/.hidden.ts', 'other/keep.txt']) write(root, name);
  const glob = require('glob');
  const asyncGlob = promisify(glob);
  const cases = [
    ['src/**/*.{ts,js}', {}, ['src/a.ts', 'src/b.js', 'src/nested/c.ts']],
    ['src/**/*.ts', { dot: true }, ['src/.hidden.ts', 'src/a.ts', 'src/nested/c.ts']],
    ['src/**/!(*.js)', { nodir: true }, ['src/a.ts', 'src/nested/c.ts']],
    ['src/**/*.ts', { ignore: 'src/nested/**' }, ['src/a.ts']],
    ['missing/*.ts', { nonull: true }, ['missing/*.ts']],
  ];
  for (const [pattern, options, expected] of cases) {
    assert.deepEqual(glob.sync(pattern, { cwd: root, ...options }).sort(), expected.sort());
    assert.deepEqual((await asyncGlob(pattern, { cwd: root, ...options })).sort(), expected.sort());
  }
  assert.equal(glob.hasMagic('src/*.ts'), true);
  assert.equal(glob.hasMagic('src/a.ts'), false);
});

test('actual rimraf callback cleanup removes only selected synthetic files and never follows a symlink', async t => {
  const root = fixture(t);
  write(root, 'remove/a.tmp'); write(root, 'remove/b.tmp'); write(root, 'remove/keep.txt');
  write(root, 'outside/keep.txt');
  fs.symlinkSync(path.join(root, 'outside'), path.join(root, 'remove', 'link'), 'dir');
  const rimraf = promisify(require('rimraf'));
  await rimraf(path.join(root, 'remove', '*.tmp'));
  assert.deepEqual(fs.readdirSync(path.join(root, 'remove')).sort(), ['keep.txt', 'link']);
  await rimraf(path.join(root, 'remove'));
  assert.equal(fs.existsSync(path.join(root, 'remove')), false);
  assert.equal(fs.readFileSync(path.join(root, 'outside/keep.txt'), 'utf8'), '');
});

test('real user-data-dir plugin cleanup preserves existing profiles and deletes disposable temporary profiles', async t => {
  const root = fixture(t);
  const pluginFactory = require('puppeteer-extra-plugin-user-data-dir');
  const existing = path.join(root, 'existing');
  write(existing, 'keep.txt', 'preserve');
  const persistent = pluginFactory({ folderPath: root });
  await persistent.beforeLaunch({ userDataDir: existing });
  await persistent.onDisconnected();
  assert.equal(fs.readFileSync(path.join(existing, 'keep.txt'), 'utf8'), 'preserve');
  const temporary = pluginFactory({ folderPath: root });
  const options = {};
  await temporary.beforeLaunch(options); // Only local directory lifecycle, no browser.
  assert.equal(path.dirname(options.userDataDir), root);
  write(options.userDataDir, 'Default/Preferences', '{}');
  await temporary.onDisconnected();
  for (let i = 0; i < 200 && fs.existsSync(options.userDataDir); i++) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  assert.equal(fs.existsSync(options.userDataDir), false);
  assert.equal(fs.existsSync(existing), true);
});

test('actual ESLint file enumeration, eslintrc overrides and flat config include/exclude paths', async t => {
  const root = fixture(t);
  write(root, 'src/good.js', 'const x = 1;\n');
  write(root, 'src/bad.js', 'debugger;\n');
  write(root, 'ignored/bad.js', 'debugger;\n');
  const { ESLint } = require('eslint');
  const eslint = new ESLint({ cwd: root, useEslintrc: false, overrideConfig: {
    parserOptions: { ecmaVersion: 2022 }, ignorePatterns: ['ignored/**'],
    overrides: [{ files: ['src/**/*.js'], rules: { 'no-debugger': 'error' } }],
  } });
  const results = await eslint.lintFiles(['**/*.js']);
  assert.equal(results.length, 2);
  assert.equal(results.find(r => r.filePath.endsWith('good.js')).errorCount, 0);
  assert.equal(results.find(r => r.filePath.endsWith('bad.js')).errorCount, 1);
  const { ConfigArray } = require('@humanwhocodes/config-array');
  const configs = new ConfigArray([{ files: ['src/**/*.js'], ignores: ['**/bad.js'] }], { basePath: root });
  await configs.normalize();
  assert.notEqual(configs.getConfig(path.join(root, 'src/good.js')), undefined);
  assert.equal(configs.getConfig(path.join(root, 'src/bad.js')), undefined);
});

test('actual nodemon matcher retains extension and ignore filtering without starting a watcher', () => {
  const match = require('nodemon/lib/monitor/match');
  const files = ['src/a.ts', 'src/b.js', 'src/.hidden.ts', 'dist/generated.ts'];
  const result = match(files, ['**/*', '!**/dist/**'], 'ts');
  assert.deepEqual(result.result.sort(), ['src/a.ts', 'src/.hidden.ts'].map(p => path.resolve(p)).sort());
});

test('actual TypeScript project service admits only matching default-project files', t => {
  const root = fixture(t);
  const parser = require('@typescript-eslint/parser');
  const settings = {
    tsconfigRootDir: root,
    projectService: { allowDefaultProject: ['*.ts'] },
  };
  const admitted = parser.parseForESLint('const value: number = 1;', { ...settings, filePath: path.join(root, '.fixture.ts') });
  assert.ok(admitted.services.program);
  assert.throws(() => parser.parseForESLint('const value = 1;', { ...settings, filePath: path.join(root, 'nested/denied.ts') }), /not found|allowDefaultProject/);
  parser.clearCaches();
});
