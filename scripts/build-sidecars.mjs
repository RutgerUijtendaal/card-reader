#!/usr/bin/env node

import { existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, '..');

const binariesDir = join(repoRoot, 'apps', 'desktop', 'src-tauri', 'binaries');
const pyinstallerTmpDir = join(repoRoot, '.tmp', 'pyinstaller');
const addDataSeparator = process.platform === 'win32' ? ';' : ':';
const pyinstallerHooksDir = join(repoRoot, 'scripts', 'pyinstaller-hooks');

const run = (command, args, cwd = repoRoot, env = {}) => {
  const result = spawnSync(command, args, {
    cwd,
    stdio: 'inherit',
    shell: false,
    env: { ...process.env, ...env }
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
};

const clean = () => {
  rmSync(binariesDir, { recursive: true, force: true });
  rmSync(pyinstallerTmpDir, { recursive: true, force: true });
  mkdirSync(binariesDir, { recursive: true });
  mkdirSync(pyinstallerTmpDir, { recursive: true });
};

const buildApi = () => {
  const apiEntry = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'main.py');
  const seedUsersFile = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'seeds', 'seed-users.local.json');
  const seedUsersDataSpec = `${seedUsersFile}${addDataSeparator}seeds`;

  const pyinstallerArgs = [
    'run',
    '--project',
    'services/api',
    '--with',
    'pyinstaller',
    'pyinstaller',
    '--noconfirm',
    '--clean',
    '--onefile',
    '--name',
    'card-reader-api',
    '--distpath',
    binariesDir,
    '--workpath',
    join(pyinstallerTmpDir, 'api'),
    '--specpath',
    join(pyinstallerTmpDir, 'spec'),
    '--additional-hooks-dir',
    pyinstallerHooksDir,
    apiEntry
  ];

  if (existsSync(seedUsersFile)) {
    pyinstallerArgs.splice(pyinstallerArgs.length - 1, 0, '--add-data', seedUsersDataSpec);
  }

  run('uv', pyinstallerArgs, repoRoot, {
    DJANGO_SETTINGS_MODULE: 'card_reader_api.project.settings'
  });
};

const buildParser = () => {
  const parserEntry = join(repoRoot, 'services', 'parser', 'src', 'card_reader_parser', 'main.py');

  run('uv', [
    'run',
    '--project',
    'services/parser',
    '--with',
    'pyinstaller',
    'pyinstaller',
    '--noconfirm',
    '--clean',
    '--onefile',
    '--name',
    'card-reader-parser',
    '--distpath',
    binariesDir,
    '--workpath',
    join(pyinstallerTmpDir, 'parser'),
    '--specpath',
    join(pyinstallerTmpDir, 'spec'),
    '--additional-hooks-dir',
    pyinstallerHooksDir,
    '--collect-all',
    'paddleocr',
    '--collect-all',
    'paddlex',
    '--collect-all',
    'paddle',
    '--collect-all',
    'cv2',
    '--collect-all',
    'shapely',
    '--collect-binaries',
    'paddle',
    '--copy-metadata',
    'paddlex',
    '--copy-metadata',
    'paddleocr',
    '--copy-metadata',
    'paddlepaddle',
    '--copy-metadata',
    'imagesize',
    '--copy-metadata',
    'opencv-contrib-python',
    '--copy-metadata',
    'pyclipper',
    '--copy-metadata',
    'pypdfium2',
    '--copy-metadata',
    'python-bidi',
    '--copy-metadata',
    'shapely',
    parserEntry
  ], repoRoot, {
    DJANGO_SETTINGS_MODULE: 'card_reader_core.django_settings'
  });
};

clean();
buildApi();
buildParser();
