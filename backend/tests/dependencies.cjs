const test = require('node:test');
const assert = require('node:assert/strict');

test('Playwright extra accepts the stealth plugin without Puppeteer runtime', () => {
  const { chromium } = require('playwright-extra');
  const plugin = require('puppeteer-extra-plugin-stealth')();
  plugin.enabledEvasions.delete('iframe.contentWindow');
  plugin.enabledEvasions.delete('media.codecs');
  assert.equal(plugin.enabledEvasions.has('iframe.contentWindow'), false);
  assert.equal(chromium.use(plugin), chromium);
  assert.equal(typeof chromium.launch, 'function');
  // No browser launch, meeting, capture device or external request.
});

test('GCS v8 local client construction and object naming contract', () => {
  const { Storage } = require('@google-cloud/storage');
  const client = new Storage({ projectId: 'synthetic-project', credentials: { client_email: 'fixture@example.invalid', private_key: 'not-a-real-key' } });
  const file = client.bucket('synthetic-bucket').file('synthetic/image.png');
  assert.equal(file.name, 'synthetic/image.png');
  assert.equal(typeof file.save, 'function');
});

test('remaining UUID advisory is not on MSAL v4 call shape', () => {
  const fs = require('node:fs');
  const entry = require.resolve('@azure/msal-node');
  const code = fs.readFileSync(entry, 'utf8');
  assert.ok(code.includes('uuid.v4()'));
  assert.equal(/uuid\.v[356]\(/.test(code), false);
});
