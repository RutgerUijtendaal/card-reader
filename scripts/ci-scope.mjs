import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const ALL_SCOPES = Object.freeze({
  ocr: true,
  macos_dependencies: true,
  portability: true,
});

const PYTHON_DEPENDENCY_FILES = new Set(['.python-version', 'pyproject.toml', 'uv.lock']);

function normalizePath(filePath) {
  return filePath.replaceAll('\\', '/').replace(/^\.\//, '');
}

function isPythonManifest(filePath) {
  return (
    PYTHON_DEPENDENCY_FILES.has(filePath) || /^services\/[^/]+\/pyproject\.toml$/.test(filePath)
  );
}

function isWorkflow(filePath) {
  return filePath.startsWith('.github/workflows/');
}

function affectsOcr(filePath) {
  return (
    filePath.startsWith('services/parser/') ||
    filePath.startsWith('services/integration/') ||
    filePath.startsWith('services/core/') ||
    filePath.startsWith('services/api/src/card_reader_api/project/') ||
    filePath === 'scripts/ci-scope.mjs' ||
    isPythonManifest(filePath) ||
    isWorkflow(filePath)
  );
}

function affectsMacosDependencies(filePath) {
  return (
    filePath === 'scripts/check-native-platform.mjs' ||
    filePath === 'scripts/native-platform-support.mjs' ||
    filePath === 'scripts/ci-scope.mjs' ||
    isPythonManifest(filePath) ||
    isWorkflow(filePath)
  );
}

function affectsPortability(filePath) {
  return (
    filePath.startsWith('docker/') ||
    filePath.startsWith('services/core/src/') ||
    filePath.startsWith('services/parser/src/') ||
    filePath === 'docker-compose.yml' ||
    filePath === 'docker-compose.local.yml' ||
    filePath === '.env.example' ||
    filePath === 'scripts/create-backup.sh' ||
    filePath === 'scripts/restore-backup.sh' ||
    filePath === 'scripts/check-native-platform.mjs' ||
    filePath === 'scripts/native-platform-support.mjs' ||
    filePath === 'scripts/ci-scope.mjs' ||
    isPythonManifest(filePath) ||
    isWorkflow(filePath)
  );
}

export function detectCiScopes(
  changedPaths,
  { forceAll = false, comparisonAvailable = true } = {},
) {
  if (forceAll || !comparisonAvailable) {
    return { ...ALL_SCOPES };
  }

  const paths = changedPaths.map(normalizePath);
  return {
    ocr: paths.some(affectsOcr),
    macos_dependencies: paths.some(affectsMacosDependencies),
    portability: paths.some(affectsPortability),
  };
}

export function resolveCiScopes({
  eventName,
  baseSha,
  headSha,
  loadChangedPaths,
  reportError = console.error,
} = {}) {
  if (eventName === 'schedule' || eventName === 'workflow_dispatch') {
    return detectCiScopes([], { forceAll: true });
  }

  const validBase = Boolean(baseSha) && !/^0+$/.test(baseSha);
  if (!validBase || !headSha) {
    return detectCiScopes([], { comparisonAvailable: false });
  }

  try {
    const paths = loadChangedPaths(baseSha, headSha);
    return detectCiScopes(paths);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    reportError(`Unable to determine changed paths; enabling all CI scopes: ${detail}`);
    return detectCiScopes([], { comparisonAvailable: false });
  }
}

function loadChangedPaths(baseSha, headSha) {
  return execFileSync(
    'git',
    ['diff', '--name-only', '--diff-filter=ACMR', `${baseSha}...${headSha}`],
    { encoding: 'utf8' },
  )
    .split(/\r?\n/)
    .filter(Boolean);
}

function printGithubOutputs(scopes) {
  for (const [scope, enabled] of Object.entries(scopes)) {
    console.log(`${scope}=${enabled}`);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  printGithubOutputs(
    resolveCiScopes({
      eventName: process.env.CI_EVENT_NAME,
      baseSha: process.env.CI_BASE_SHA,
      headSha: process.env.CI_HEAD_SHA,
      loadChangedPaths,
      reportError: console.error,
    }),
  );
}
