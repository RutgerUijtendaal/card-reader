import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const packageJson = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));

test('bootstrap invokes the repository dependency setup script explicitly', () => {
  assert.equal(packageJson.scripts.setup, undefined);
  assert.equal(packageJson.scripts['setup:deps'], 'pnpm deps:js && pnpm deps:py');
  assert.match(packageJson.scripts['bootstrap:dev'], /^pnpm run setup:deps && /);
  assert.match(packageJson.scripts['bootstrap:dev:reset'], /^pnpm run setup:deps && /);
});
