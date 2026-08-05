import process from 'node:process';

export const supportedNativePlatforms = new Set(['darwin-arm64', 'linux-x64', 'win32-x64']);

export function getNativePlatformSupport(platform = process.platform, architecture = process.arch) {
  const key = `${platform}-${architecture}`;
  return {
    key,
    supported: supportedNativePlatforms.has(key),
  };
}

export function requiresAmd64EmulationProbe(
  platform = process.platform,
  architecture = process.arch,
) {
  return architecture !== 'x64' && !getNativePlatformSupport(platform, architecture).supported;
}

export function unsupportedNativePlatformMessage(platformKey) {
  return [
    `Native parser dependencies are not available for ${platformKey}.`,
    'Supported native development platforms are macOS ARM64, Linux x86_64, and Windows x86_64.',
    'Use Docker Compose with amd64 emulation for Python services; run the frontend separately.',
  ].join('\n');
}
