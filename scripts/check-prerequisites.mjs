import { spawnSync } from 'node:child_process';
import process from 'node:process';

const links = {
  docker: 'https://docs.docker.com/get-started/get-docker/',
  node: 'https://nodejs.org/en/download',
  pnpm: 'https://pnpm.io/installation',
  uv: 'https://docs.astral.sh/uv/getting-started/installation/',
};

let failureCount = 0;

function report(status, label, detail) {
  console.log(`${status.padEnd(4)} ${label}: ${detail}`);
}

function fail(label, detail) {
  failureCount += 1;
  report('FAIL', label, detail);
}

function pass(label, detail) {
  report('PASS', label, detail);
}

function warn(label, detail) {
  report('WARN', label, detail);
}

function parseVersion(value) {
  const match = value.match(/(\d+)\.(\d+)(?:\.(\d+))?/);
  if (!match) {
    return null;
  }
  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: Number(match[3] ?? 0),
    text: `${match[1]}.${match[2]}.${match[3] ?? 0}`,
  };
}

function runTool(command, args) {
  const isWindows = process.platform === 'win32';
  const executable = isWindows ? (process.env.ComSpec ?? 'cmd.exe') : command;
  const executableArgs = isWindows ? ['/d', '/s', '/c', [command, ...args].join(' ')] : args;
  const result = spawnSync(executable, executableArgs, {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const output = `${result.stdout ?? ''}\n${result.stderr ?? ''}`.trim();
  return { ok: result.status === 0, output };
}

function runExecutable(executable, args) {
  const result = spawnSync(executable, args, {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const output = `${result.stdout ?? ''}\n${result.stderr ?? ''}`.trim();
  return { ok: result.status === 0, output };
}

console.log('Checking Card Reader prerequisites...');

const nodeVersion = parseVersion(process.versions.node);
if (nodeVersion && nodeVersion.major >= 22) {
  pass('Node.js', `${nodeVersion.text} (requires 22+)`);
} else {
  fail('Node.js', `22+ is required. Install or upgrade: ${links.node}`);
}

const pnpmUserAgent = process.env.npm_config_user_agent ?? '';
const pnpmUserAgentVersion = pnpmUserAgent.match(/pnpm\/(\d+\.\d+(?:\.\d+)?)/)?.[1];
const pnpmResult = pnpmUserAgentVersion
  ? { ok: true, output: pnpmUserAgentVersion }
  : runTool('pnpm', ['--version']);
const pnpmVersion = parseVersion(pnpmResult.output);
if (pnpmResult.ok && pnpmVersion && pnpmVersion.major >= 10) {
  pass('pnpm', `${pnpmVersion.text} (requires 10+)`);
} else {
  fail('pnpm', `10+ is required. Install or upgrade: ${links.pnpm}`);
}

const uvResult = runTool('uv', ['--version']);
if (uvResult.ok) {
  pass('uv', uvResult.output.split(/\r?\n/, 1)[0]);
} else {
  fail('uv', `not found. Install it before bootstrapping: ${links.uv}`);
}

if (uvResult.ok) {
  const pythonPathResult = runTool('uv', ['python', 'find']);
  const pythonPath = pythonPathResult.output.split(/\r?\n/).filter(Boolean).at(-1) ?? '';
  const pythonResult =
    pythonPathResult.ok && pythonPath
      ? runExecutable(pythonPath, ['--version'])
      : { ok: false, output: '' };
  const pythonVersion = parseVersion(pythonResult.output);
  if (
    pythonResult.ok &&
    pythonVersion &&
    pythonVersion.major === 3 &&
    [12, 13].includes(pythonVersion.minor)
  ) {
    pass('Python', `${pythonVersion.text} selected by uv`);
  } else {
    fail(
      'Python',
      '3.12 or 3.13 is required. Install the pinned version with: uv python install 3.12',
    );
  }
}

const dockerResult = runTool('docker', ['--version']);
if (dockerResult.ok) {
  pass('Docker', `${dockerResult.output.split(/\r?\n/, 1)[0]} (optional)`);
} else {
  warn(
    'Docker',
    `optional for native development; install it for container workflows: ${links.docker}`,
  );
}

if (failureCount > 0) {
  console.error(`\nPrerequisite check failed with ${failureCount} issue(s).`);
  process.exit(1);
}

console.log(
  '\nRequired system tools are ready. Run pnpm bootstrap:dev to install project dependencies.',
);
