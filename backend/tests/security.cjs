const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { authorizeDispatch, validateJoin, validUserId } = require('../src/security/dispatch');
const { recordingFolder, recordingFile } = require('../src/security/paths');
const { redact } = require('../src/security/redact');

function invoke(fn, req) {
  let status = 200, next = 0;
  const res = { status(n) { status = n; return this; }, json() { return this; } };
  fn(req, res, () => { next++; });
  return { status, next };
}
test('auth fail-closed before jobs or IO, independent from upload token', () => {
  delete process.env.MEETINGBOT_DISPATCH_TOKEN;
  assert.equal(invoke(authorizeDispatch, { get: () => undefined }).status, 503);
  process.env.MEETINGBOT_DISPATCH_TOKEN = 'synthetic-dispatch-fixture-'.repeat(2);
  assert.equal(invoke(authorizeDispatch, { get: () => 'Bearer invalid', body: { bearerToken: 'upload' } }).next, 0);
  assert.equal(invoke(authorizeDispatch, { get: () => `Bearer ${process.env.MEETINGBOT_DISPATCH_TOKEN}` }).next, 1);
  delete process.env.MEETINGBOT_DISPATCH_TOKEN;
});
test('URL and userId reject traversal and unrelated hosts before dispatch', () => {
  for (const id of ['../outside', '/absolute', '..', 'a/b', 'a\\b', '%2e%2e', '', null]) assert.equal(validUserId(id), false);
  for (const url of ['http://meet.google.com/a', 'https://meet.google.com.evil.test/a', 'https://user@meet.google.com/a', 'https://localhost/a']) {
    assert.equal(invoke(validateJoin, { baseUrl: '/google', body: { userId: 'test', url } }).next, 0);
  }
  assert.equal(invoke(validateJoin, { baseUrl: '/google', body: { userId: 'test_1', url: 'https://meet.google.com/abc-defg-hij' } }).next, 1);
});
test('paths refuse directory and file symlinks without touching outside fixtures', () => {
  const tmp = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'meeting-path-')));
  try {
    const root = path.join(tmp, 'recordings'); fs.mkdirSync(root);
    const outside = path.join(tmp, 'outside'); fs.mkdirSync(outside);
    for (const id of ['../outside', '/outside', 'a/b']) assert.throws(() => recordingFolder(root, id));
    fs.symlinkSync(outside, path.join(root, 'evil'));
    assert.throws(() => recordingFolder(root, 'evil'));
    fs.mkdirSync(path.join(root, 'safe'));
    fs.symlinkSync(path.join(outside, 'file'), path.join(root, 'safe', 'clip.webm'));
    assert.throws(() => recordingFile(root, 'safe', 'clip', '.webm'));
    assert.throws(() => recordingFile(root, 'safe', '../clip', '.webm'));
    assert.throws(() => recordingFile(root, 'safe', 'clip', '/../file'));
    assert.equal(recordingFile(root, 'safe', 'other', '.webm'), path.join(root, 'safe', 'other.webm'));
    assert.deepEqual(fs.readdirSync(outside), []);
  } finally { fs.rmSync(tmp, { recursive: true }); }
});
test('redacts nested Axios config, URLs, bearer strings and cycles', () => {
  const value = { config: { headers: { Authorization: 'Bearer synthetic' } }, message: 'Bearer synthetic https://example.test/?token=synthetic', error: new Error('synthetic') };
  value.self = value;
  const output = JSON.stringify(redact(value));
  assert.equal(output.includes('synthetic'), false);
  assert.equal(output.includes('example.test'), false);
});
test('actual source wiring guards routes and disk writes', () => {
  const app = fs.readFileSync(path.join(__dirname, '../src/app/index.ts'), 'utf8');
  assert.ok(app.indexOf('app.use(authorizeDispatch)') >= 0);
  assert.ok(app.indexOf('app.use(authorizeDispatch)') < app.indexOf('app.use(express.json'));
  for (const p of ['google', 'microsoft', 'zoom']) assert.ok(app.includes(`app.use('/${p}', validateJoin, ${p}Router)`));
  const disk = fs.readFileSync(path.join(__dirname, '../src/middleware/disk-uploader.ts'), 'utf8');
  assert.ok(disk.includes('recordingFolder(tempFolder, userId)'));
  assert.ok(disk.includes('O_NOFOLLOW'));
  assert.ok(fs.readFileSync(path.join(__dirname, '../docker-compose.yml'), 'utf8').includes('127.0.0.1:3001:3001'));
});
