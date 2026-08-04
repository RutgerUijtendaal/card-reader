import {
  getNativePlatformSupport,
  unsupportedNativePlatformMessage,
} from './native-platform-support.mjs';

const nativePlatform = getNativePlatformSupport();

if (!nativePlatform.supported) {
  console.error(unsupportedNativePlatformMessage(nativePlatform.key));
  process.exit(1);
}
