#!/usr/bin/env node

import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, '..');

const binariesDir = join(repoRoot, 'apps', 'desktop', 'src-tauri', 'binaries');
const pyinstallerTmpDir = join(repoRoot, '.tmp', 'pyinstaller');
const isWindows = process.platform === 'win32';
const addDataSeparator = isWindows ? ';' : ':';

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
  const apiEntry = join(repoRoot, 'services', 'api', 'src', 'main.py');
  const apiPath = join(repoRoot, 'services', 'api', 'src');
  const corePath = join(repoRoot, 'services', 'core', 'src');
  const seedFile = join(repoRoot, 'services', 'core', 'seeds', 'keywords.txt');
  const dataSpec = `${seedFile}${addDataSeparator}core/seeds`;

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
    dataSpec,
    apiEntry
  ]);
};

const buildParser = () => {
  const parserEntry = join(repoRoot, 'services', 'parser', 'src', 'main.py');
  const parserPath = join(repoRoot, 'services', 'parser', 'src');
  const corePath = join(repoRoot, 'services', 'core', 'src');
  const templateDir = join(repoRoot, 'services', 'parser', 'src', 'parsers', 'templates');
  const dataSpec = `${templateDir}${addDataSeparator}parsers/templates`;

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
    '--add-data',
    dataSpec,
    parserEntry
  ]);
};

const duplicateWindowsExes = () => {
  if (!isWindows) {
    return;
  }

  const copyIfExists = (fromName, toName) => {
    const from = join(binariesDir, fromName);
    const to = join(binariesDir, toName);
    if (existsSync(from)) {
      cpSync(from, to);
    }
  };

  copyIfExists('card-reader-api.exe', 'card-reader-api');
  copyIfExists('card-reader-parser.exe', 'card-reader-parser');
};

clean();
buildApi();
buildParser();
duplicateWindowsExes();

