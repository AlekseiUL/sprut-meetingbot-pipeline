const test = require('node:test');
const assert = require('node:assert/strict');
const { ESLint } = require('eslint');

function checkToolchain(parserVersion, pluginVersion) {
  assert.equal(parserVersion, pluginVersion, 'TypeScript parser/plugin must update together');
}

test('installed TypeScript parser and plugin are the same reviewed version', () => {
  checkToolchain(
    require('@typescript-eslint/parser/package.json').version,
    require('@typescript-eslint/eslint-plugin/package.json').version,
  );
});

test('mixed parser/plugin majors are rejected', () => {
  assert.throws(() => checkToolchain('8.72.0', '5.62.0'), /must update together/);
});

test('the configured TypeScript lint engine rejects invalid syntax', async () => {
  const eslint = new ESLint({ fix: false });
  const [valid] = await eslint.lintText('const value: number = 1;\nexport { value };\n', { filePath: 'src/toolchain-fixture.ts' });
  assert.equal(valid.errorCount, 0);
  const [invalid] = await eslint.lintText('const value: = ;\n', { filePath: 'src/toolchain-fixture.ts' });
  assert.ok(invalid.fatalErrorCount > 0);
});
