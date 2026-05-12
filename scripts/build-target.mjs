#!/usr/bin/env node

import { execSync } from "node:child_process";

const platform = process.platform;

if (platform === "win32") {
  execSync("tauri build --bundles nsis", { stdio: "inherit" });
} else if (platform === "linux") {
  execSync("tauri build --bundles appimage,deb", { stdio: "inherit" });
} else if (platform === "darwin") {
  execSync("tauri build --bundles dmg", { stdio: "inherit" });
}