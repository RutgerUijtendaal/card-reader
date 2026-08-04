import process from 'node:process';

const supportedPlatforms = new Set(['darwin-arm64', 'linux-x64', 'win32-x64']);
const currentPlatform = `${process.platform}-${process.arch}`;

if (!supportedPlatforms.has(currentPlatform)) {
  console.error(
    [
      `Native parser dependencies are not available for ${currentPlatform}.`,
      'Supported native development platforms are macOS ARM64, Linux x86_64, and Windows x86_64.',
      'Use Docker Compose with amd64 emulation for Python services; run the frontend separately.',
    ].join('\n'),
  );
  process.exit(1);
}
