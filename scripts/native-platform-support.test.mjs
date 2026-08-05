import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getNativePlatformSupport,
  unsupportedNativePlatformMessage,
} from './native-platform-support.mjs';

test('recognizes every supported native development platform', () => {
  assert.equal(getNativePlatformSupport('darwin', 'arm64').supported, true);
  assert.equal(getNativePlatformSupport('linux', 'x64').supported, true);
  assert.equal(getNativePlatformSupport('win32', 'x64').supported, true);
});

test('requires the container workflow on unsupported native platforms', () => {
  const platform = getNativePlatformSupport('darwin', 'x64');

  assert.deepEqual(platform, { key: 'darwin-x64', supported: false });
  assert.match(unsupportedNativePlatformMessage(platform.key), /Use Docker Compose/);
});
