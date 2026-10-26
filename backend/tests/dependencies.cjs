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

test('MSAL resolves patched UUID and keeps the reviewed v4-only surface', () => {
  const fs = require('node:fs');
  const { createRequire } = require('node:module');
  const entry = require.resolve('@azure/msal-node');
  const fromMsal = createRequire(entry);
  assert.equal(fromMsal('uuid/package.json').version, '11.1.1');
  const code = fs.readFileSync(entry, 'utf8');
  assert.deepEqual([...new Set([...code.matchAll(/uuid\.(\w+)/g)].map(m => m[1]))], ['v4']);
  const uuid = fromMsal('uuid');
  for (const method of ['v3', 'v5']) {
    assert.throws(() => uuid[method]('synthetic', uuid[method].DNS, Buffer.alloc(2)), RangeError);
  }
});

test('actual MSAL CryptoProvider GUID and PKCE work with the reviewed UUID override', async () => {
  const { CryptoProvider } = require('@azure/msal-node');
  const { createHash } = require('node:crypto');
  const provider = new CryptoProvider();
  const values = new Set();
  for (let i = 0; i < 100; i++) {
    const value = provider.createNewGuid();
    assert.match(value, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    values.add(value);
  }
  assert.equal(values.size, 100);
  const codes = await provider.generatePkceCodes();
  assert.equal(codes.challenge, createHash('sha256').update(codes.verifier).digest('base64url'));
});

test('Azure credential and storage construction remain offline-compatible', () => {
  const { DefaultAzureCredential } = require('@azure/identity');
  const { BlobServiceClient } = require('@azure/storage-blob');
  const credential = new DefaultAzureCredential();
  assert.equal(typeof credential.getToken, 'function');
  const service = new BlobServiceClient('https://synthetic.blob.core.windows.net', credential);
  const blob = service.getContainerClient('synthetic').getBlockBlobClient('fixture.webm');
  assert.equal(typeof blob.uploadData, 'function');
  // Never getToken(), upload, read host credentials or contact any service.
});
