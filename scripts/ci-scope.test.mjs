import assert from 'node:assert/strict';
import test from 'node:test';

import { detectCiScopes, loadChangedPaths, resolveCiScopes } from './ci-scope.mjs';

test('classifies OCR, macOS dependency, and portability paths independently', () => {
  assert.deepEqual(detectCiScopes(['services/integration/tests/test_parser.py']), {
    ocr: true,
    macos_dependencies: false,
    portability: false,
    deploy: true,
  });
  assert.deepEqual(detectCiScopes(['scripts/check-native-platform.mjs']), {
    ocr: false,
    macos_dependencies: true,
    portability: true,
    deploy: true,
  });
  assert.deepEqual(detectCiScopes(['frontend/src/App.vue']), {
    ocr: false,
    macos_dependencies: false,
    portability: false,
    deploy: true,
  });
});

test('covers shared runtime, API settings, Docker, and backup scope boundaries', () => {
  assert.deepEqual(detectCiScopes(['services\\parser\\src\\card_reader_parser\\main.py']), {
    ocr: true,
    macos_dependencies: false,
    portability: true,
    deploy: true,
  });
  assert.deepEqual(detectCiScopes(['services/api/src/card_reader_api/project/test_settings.py']), {
    ocr: true,
    macos_dependencies: false,
    portability: false,
    deploy: true,
  });

  for (const changedPath of [
    '.dockerignore',
    'docker/parser.Dockerfile',
    'docker-compose.local.yml',
    'scripts/create-backup.sh',
  ]) {
    assert.deepEqual(detectCiScopes([changedPath]), {
      ocr: false,
      macos_dependencies: false,
      portability: true,
      deploy: true,
    });
  }
});

test('loads deletions and both sides of renames for scope classification', () => {
  const paths = loadChangedPaths('base', 'head', (command, args, options) => {
    assert.equal(command, 'git');
    assert.deepEqual(args, ['diff', '--name-only', '--no-renames', 'base...head']);
    assert.deepEqual(options, { encoding: 'utf8' });
    return ['docker/parser.Dockerfile', 'archive/parser.Dockerfile', '.dockerignore', ''].join(
      '\n',
    );
  });

  assert.deepEqual(paths, [
    'docker/parser.Dockerfile',
    'archive/parser.Dockerfile',
    '.dockerignore',
  ]);
  assert.equal(detectCiScopes(paths).portability, true);
});

test('shared Python and workflow changes enable every heavyweight scope', () => {
  for (const changedPath of [
    'uv.lock',
    'services/core/pyproject.toml',
    '.github/workflows/ci.yml',
  ]) {
    assert.deepEqual(detectCiScopes([changedPath]), {
      ocr: true,
      macos_dependencies: true,
      portability: true,
      deploy: true,
    });
  }
});

test('skips deployment only when every changed path is documentation', () => {
  assert.deepEqual(detectCiScopes(['AGENTS.md', 'docs/operations/deployment.md']), {
    ocr: false,
    macos_dependencies: false,
    portability: false,
    deploy: false,
  });
  assert.equal(detectCiScopes(['frontend/README.md']).deploy, false);
  assert.equal(detectCiScopes(['LICENSE']).deploy, false);
  assert.equal(detectCiScopes(['docs/README.md', 'frontend/src/App.vue']).deploy, true);
  assert.equal(detectCiScopes(['.github/workflows/ci.yml']).deploy, true);
});

test('scheduled and manual runs enable all scopes without comparing revisions', () => {
  for (const eventName of ['schedule', 'workflow_dispatch']) {
    let compared = false;
    const scopes = resolveCiScopes({
      eventName,
      baseSha: '',
      headSha: '',
      loadChangedPaths: () => {
        compared = true;
        return [];
      },
    });

    assert.deepEqual(scopes, {
      ocr: true,
      macos_dependencies: true,
      portability: true,
      deploy: true,
    });
    assert.equal(compared, false);
  }
});

test('missing and unavailable comparison bases fail open', () => {
  const missingBase = resolveCiScopes({
    eventName: 'push',
    baseSha: '0000000000000000000000000000000000000000',
    headSha: 'head',
    loadChangedPaths: () => [],
  });
  const unavailableBase = resolveCiScopes({
    eventName: 'pull_request',
    baseSha: 'base',
    headSha: 'head',
    loadChangedPaths: () => {
      throw new Error('missing object');
    },
    reportError: () => {},
  });

  assert.deepEqual(missingBase, {
    ocr: true,
    macos_dependencies: true,
    portability: true,
    deploy: true,
  });
  assert.deepEqual(unavailableBase, {
    ocr: true,
    macos_dependencies: true,
    portability: true,
    deploy: true,
  });
});
