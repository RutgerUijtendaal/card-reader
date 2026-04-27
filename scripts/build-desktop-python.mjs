#!/usr/bin/env node

import { mkdirSync, rmSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, "..");
const distDir = join(repoRoot, "dist");
const pythonVersion = process.env.CARD_READER_DESKTOP_PYTHON_VERSION ?? "3.12";
const desktopPythonDir = join(repoRoot, "apps", "desktop", "src-tauri", "python");
const runtimeDir = join(desktopPythonDir, "runtime");
const sitePackagesDir = join(desktopPythonDir, "site-packages");
const placeholderFile = join(desktopPythonDir, "placeholder.txt");
const tmpDir = join(repoRoot, ".tmp", "desktop-python");
const requirementsFile = join(tmpDir, "requirements.txt");

const run = (command, args, cwd = repoRoot, env = {}) => {
  const result = spawnSync(command, args, {
    cwd,
    stdio: "inherit",
    shell: false,
    env: { ...process.env, ...env },
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
};

const clean = () => {
  rmSync(desktopPythonDir, { recursive: true, force: true });
  rmSync(tmpDir, { recursive: true, force: true });
  rmSync(distDir, { recursive: true, force: true });
  mkdirSync(runtimeDir, { recursive: true });
  mkdirSync(sitePackagesDir, { recursive: true });
  mkdirSync(tmpDir, { recursive: true });
  mkdirSync(distDir, { recursive: true });
};

const findPythonExecutable = (rootDir) => {
  const candidates = process.platform === "win32" ? ["python.exe"] : ["python3", "python"];
  const stack = [rootDir];

  while (stack.length > 0) {
    const currentDir = stack.pop();
    for (const entry of readdirSync(currentDir, { withFileTypes: true })) {
      const fullPath = join(currentDir, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
        continue;
      }
      if (entry.isFile() && candidates.includes(entry.name)) {
        return fullPath;
      }
    }
  }

  throw new Error(`Unable to locate a Python executable under ${rootDir}`);
};

const findWheel = (prefix) => {
  const files = readdirSync(distDir);
  const match = files.find(
    (f) => f.startsWith(prefix) && f.endsWith(".whl")
  );
  if (!match) {
    throw new Error(`Wheel not found for ${prefix}`);
  }
  return join(distDir, match);
};

const buildInternalPackages = () => {
  run("uv", ["build", "services/api"]);
  run("uv", ["build", "services/core"]);
  run("uv", ["build", "services/parser"]);
};

const installRuntime = () => {
  run("uv", ["python", "install", pythonVersion, "--install-dir", runtimeDir, "--force"]);
  return findPythonExecutable(runtimeDir);
};

const exportRequirements = () => {
  run("uv", [
    "export",
    "--project",
    ".",
    "--locked",
    "--format",
    "requirements.txt",
    "--package",
    "card-reader-parser",
    "--package",
    "card-reader-api",
    "--no-dev",
    "--no-editable",
    "--no-hashes",
    "--output-file",
    requirementsFile,
  ]);
};

const installDependencies = (pythonExecutable) => {
  run("uv", [
    "pip",
    "install",
    "--python",
    pythonExecutable,
    "--target",
    sitePackagesDir,
    "--requirements",
    requirementsFile,
    "--compile-bytecode"
  ]);
};

const installInternalWheels = (pythonExecutable) => {
  run("uv", [
    "pip",
    "install",
    "--python",
    pythonExecutable,
    "--target",
    sitePackagesDir,
    "--force-reinstall",
    findWheel("card_reader_core"),
    findWheel("card_reader_parser"),
    findWheel("card_reader_api"),
    "--compile-bytecode"
  ]);
};

clean();
const runtimePython = installRuntime();

buildInternalPackages();

exportRequirements();
installDependencies(runtimePython);

installInternalWheels(runtimePython);