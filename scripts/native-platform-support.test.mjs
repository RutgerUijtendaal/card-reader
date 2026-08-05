import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getNativePlatformSupport,
  requiresAmd64EmulationProbe,
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

test('probes amd64 emulation only when an unsupported host is not x64', () => {
  assert.equal(requiresAmd64EmulationProbe('linux', 'arm64'), true);
  assert.equal(requiresAmd64EmulationProbe('win32', 'arm64'), true);
  assert.equal(requiresAmd64EmulationProbe('darwin', 'arm64'), false);
  assert.equal(requiresAmd64EmulationProbe('darwin', 'x64'), false);
});
