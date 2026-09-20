#!/usr/bin/env node
"use strict";

// Thin project-owned locator. The hook implementation remains in agent-sop-kit.

const fs = require("fs");
const childProcess = require("child_process");
const os = require("os");
const path = require("path");

function gitSiblingRoots(project) {
  try {
    const common = childProcess.execFileSync(
      "git",
      ["-C", project, "rev-parse", "--path-format=absolute", "--git-common-dir"],
      { encoding: "utf8", timeout: 2000, windowsHide: true, stdio: ["ignore", "pipe", "ignore"] }
    ).trim();
    if (!common || path.basename(common) !== ".git") return [];
    const parent = path.dirname(path.dirname(common));
    return [path.join(parent, "agent-sop-kit")];
  } catch {
    return [];
  }
}

function validRoot(root) {
  return fs.existsSync(path.join(root, "runtime", "hooks", "hook-launch.js"))
    && fs.existsSync(path.join(root, "sop-init.py"));
}

function roots() {
  const project = path.resolve(__dirname, "..", "..");
  const explicit = process.env.AGENT_SOP_KIT_ROOT;
  if (explicit && validRoot(path.resolve(explicit))) return [path.resolve(explicit)];
  const values = [];
  if (explicit) values.push(explicit);
  values.push(...gitSiblingRoots(project));
  values.push(path.join(path.dirname(project), "agent-sop-kit"));
  if ([".worktrees", "worktrees"].includes(path.basename(path.dirname(project)))) {
    values.push(path.join(path.dirname(path.dirname(project)), "agent-sop-kit"));
  }
  values.push(path.join(os.homedir(), ".local", "share", "agent-sop-kit"));
  return [...new Set(values.map((value) => path.resolve(value)))];
}

for (const root of roots()) {
  const runtime = path.join(root, "runtime", "hooks", "hook-launch.js");
  if (fs.existsSync(runtime) && fs.existsSync(path.join(root, "sop-init.py"))) {
    require(runtime);
    return;
  }
}

process.stderr.write(
  "sop hook launcher: agent-sop-kit runtime not found; deterministic guard skipped.\n"
);
