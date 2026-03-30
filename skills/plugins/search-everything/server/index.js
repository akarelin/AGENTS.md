const { spawn } = require("child_process");

const child = spawn("uvx", ["mcp-everything-search"], {
  stdio: ["pipe", "pipe", "inherit"],
  env: { ...process.env },
  shell: true,
});

process.stdin.pipe(child.stdin);
child.stdout.pipe(process.stdout);

child.on("exit", (code) => process.exit(code ?? 1));
process.on("SIGTERM", () => child.kill("SIGTERM"));
process.on("SIGINT", () => child.kill("SIGINT"));
