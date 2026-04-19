#!/usr/bin/env node

import { mkdirSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, '..');

const binariesDir = join(repoRoot, 'apps', 'desktop', 'src-tauri', 'binaries');
const pyinstallerTmpDir = join(repoRoot, '.tmp', 'pyinstaller');
const addDataSeparator = process.platform === 'win32' ? ';' : ':';

const run = (command, args, cwd = repoRoot) => {
  const result = spawnSync(command, args, {
    cwd,
    stdio: 'inherit',
    shell: false
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
  const seedKeywordsFile = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'seeds', 'keywords.json');
  const seedSymbolsFile = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'seeds', 'symbols.json');
  const seedTemplatesFile = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'seeds', 'templates.json');
  const seedAssetsDir = join(repoRoot, 'services', 'api', 'src', 'card_reader_api', 'seeds', 'assets');
  const seedKeywordsDataSpec = `${seedKeywordsFile}${addDataSeparator}seeds`;
  const seedSymbolsDataSpec = `${seedSymbolsFile}${addDataSeparator}seeds`;
  const seedTemplatesDataSpec = `${seedTemplatesFile}${addDataSeparator}seeds`;
  const seedAssetsDataSpec = `${seedAssetsDir}${addDataSeparator}seeds/assets`;
  const alembicDir = join(repoRoot, 'services', 'api', 'alembic');
  const alembicDataSpec = `${alembicDir}${addDataSeparator}alembic`;

  run('uv', [
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
    '--add-data',
    seedKeywordsDataSpec,
    '--add-data',
    seedSymbolsDataSpec,
    '--add-data',
    seedAssetsDataSpec,
    '--add-data',
    seedTemplatesDataSpec,
    '--add-data',
    alembicDataSpec,
    apiEntry
  ]);
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
  ]);
};

clean();
buildApi();
buildParser();
