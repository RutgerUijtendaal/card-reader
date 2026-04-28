#!/usr/bin/env node

import { cpSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
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
const tmpDir = join(repoRoot, ".tmp", "desktop-python");
const runtimeInstallDir = join(tmpDir, "runtime-install");
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
  mkdirSync(desktopPythonDir, { recursive: true });
  mkdirSync(sitePackagesDir, { recursive: true });
  mkdirSync(tmpDir, { recursive: true });
  mkdirSync(runtimeInstallDir, { recursive: true });
  mkdirSync(distDir, { recursive: true });
};

const findPythonExecutable = (rootDir) => {
  const candidates = process.platform === "win32"
    ? ["python.exe"]
    : ["python3.12", "python3", "python"];
  const stack = [rootDir];

  while (stack.length > 0) {
    const currentDir = stack.pop();
    for (const entry of readdirSync(currentDir, { withFileTypes: true })) {
      const fullPath = join(currentDir, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
        continue;
      }
      if ((entry.isFile() || entry.isSymbolicLink()) && candidates.includes(entry.name)) {
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

const derivePythonHome = (pythonExecutable) => {
  const parent = dirname(pythonExecutable);
  return basename(parent) === "bin"
    ? dirname(parent)
    : parent;
};

const removeIfExists = (targetPath) => {
  if (!existsSync(targetPath)) {
    return;
  }
  rmSync(targetPath, { recursive: true, force: true });
};

const pruneUnusedRuntimeFiles = () => {
  const dynloadDir = join(runtimeDir, "lib", `python${pythonVersion}`, "lib-dynload");
  const removalTargets = [
    join(runtimeDir, "tcl"),
    join(runtimeDir, "DLLs", "_tkinter.pyd"),
    join(runtimeDir, "Lib", "tkinter"),
    join(runtimeDir, "Lib", "idlelib"),
    join(runtimeDir, "Lib", "turtledemo"),
    join(runtimeDir, "lib", `python${pythonVersion}`, "tkinter"),
    join(runtimeDir, "lib", `python${pythonVersion}`, "idlelib"),
    join(runtimeDir, "lib", `python${pythonVersion}`, "turtledemo"),
    join(runtimeDir, "lib", "libtcl9.0.so"),
    join(runtimeDir, "lib", "libtk9.0.so"),
  ];

  for (const targetPath of removalTargets) {
    removeIfExists(targetPath);
  }

  if (existsSync(dynloadDir)) {
    for (const entry of readdirSync(dynloadDir, { withFileTypes: true })) {
      if (entry.isFile() && entry.name.startsWith("_tkinter.")) {
        removeIfExists(join(dynloadDir, entry.name));
      }
    }
  }
};

const buildInternalPackages = () => {
  run("uv", ["build", "services/api"]);
  run("uv", ["build", "services/core"]);
  run("uv", ["build", "services/parser"]);
};

const installRuntime = () => {
  run("uv", ["python", "install", pythonVersion, "--install-dir", runtimeInstallDir, "--force"]);
  const pythonExecutable = findPythonExecutable(runtimeInstallDir);
  const pythonHome = derivePythonHome(pythonExecutable);
  cpSync(pythonHome, runtimeDir, {
    recursive: true,
    force: true,
    dereference: true,
  });
  pruneUnusedRuntimeFiles();
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
