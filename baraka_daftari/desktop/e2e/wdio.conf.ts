// tauri-driver + Microsoft Edge WebDriver (msedgedriver) — faqat Windows. Ishga tushirish: e2e/README.md.
import { spawn, type ChildProcess } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';

let driver: ChildProcess | undefined;

export const config = {
  runner: 'local',
  specs: ['./specs/**/*.e2e.ts'],
  maxInstances: 1,
  hostname: '127.0.0.1',
  port: 4444,
  capabilities: [
    {
      maxInstances: 1,
      'tauri:options': {
        // Reliz build: `cargo tauri build --no-bundle` → target/release/baraka-desktop.exe
        application: path.resolve('..', 'target', 'release', 'baraka-desktop.exe'),
      },
    },
  ],
  framework: 'mocha',
  reporters: ['spec'],
  mochaOpts: { ui: 'bdd', timeout: 120_000 },
  onPrepare: () => {
    driver = spawn(path.join(os.homedir(), '.cargo', 'bin', 'tauri-driver'), [], {
      stdio: [null, process.stdout, process.stderr],
    });
  },
  onComplete: () => {
    driver?.kill();
  },
};
