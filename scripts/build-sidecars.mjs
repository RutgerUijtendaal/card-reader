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
  const apiPath = join(repoRoot, 'services', 'api', 'src');
  const corePath = join(repoRoot, 'services', 'core', 'src');
  const coreMigrationsDir = join(
    repoRoot,
    'services',
    'core',
    'src',
    'card_reader_core',
    'migrations'
  );
  const seedKeywordsFile = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'seeds', 'seed-keywords.json');
  const seedSymbolsFile = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'seeds', 'seed-symbols.json');
  const seedTemplatesFile = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'seeds', 'seed-templates.json');
  const seedUsersFile = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'seeds', 'seed-users.local.json');
  const seedAssetsDir = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'seeds', 'assets');
  const coreMigrationsDataSpec = `${coreMigrationsDir}${addDataSeparator}card_reader_core/migrations`;
  const seedKeywordsDataSpec = `${seedKeywordsFile}${addDataSeparator}seeds`;
  const seedSymbolsDataSpec = `${seedSymbolsFile}${addDataSeparator}seeds`;
  const seedTemplatesDataSpec = `${seedTemplatesFile}${addDataSeparator}seeds`;
  const seedUsersDataSpec = `${seedUsersFile}${addDataSeparator}seeds`;
  const seedAssetsDataSpec = `${seedAssetsDir}${addDataSeparator}seeds/assets`;

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
    '--paths',
    apiPath,
    '--paths',
    corePath,
    '--hidden-import',
    'card_reader_api.apps',
    '--hidden-import',
    'card_reader_core.apps',
    '--add-data',
    coreMigrationsDataSpec,
    '--add-data',
    seedKeywordsDataSpec,
    '--add-data',
    seedSymbolsDataSpec,
    '--add-data',
    seedAssetsDataSpec,
    '--add-data',
    seedTemplatesDataSpec,
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
  const parserPath = join(repoRoot, 'services', 'parser', 'src');
  const corePath = join(repoRoot, 'services', 'core', 'src');

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
    '--paths',
    parserPath,
    '--paths',
    corePath,
    '--hidden-import',
    'card_reader_core.apps',
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
