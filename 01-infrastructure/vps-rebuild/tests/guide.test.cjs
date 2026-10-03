const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
const file = path.resolve(__dirname, '../VPS重建与网站部署一步步教程.html');
let logic;
function api() {
  assert.ok(fs.existsSync(file), '教程尚未生成');
  if (!logic) {
    const html = fs.readFileSync(file, 'utf8');
    const match = html.match(/\/\* GUIDE_LOGIC_START \*\/([\s\S]*?)\/\* GUIDE_LOGIC_END \*\//);
    assert.ok(match, '参数生成逻辑缺失');
    logic = {}; vm.createContext(logic); vm.runInContext(match[1], logic);
  }
  return logic;
}
test('accepted settings produce actual SSH and website commands', () => {
  const { parseSettings, renderTemplate } = api();
  const s = parseSettings('203.0.113.42', 'finance.example.com', 'panel-abc');
  assert.equal(s.PANEL_PATH, '/panel-abc/');
  assert.equal(renderTemplate('ssh deployer@{{IP}}; https://{{DOMAIN}}; {{PANEL_PATH}}', s),
    'ssh deployer@203.0.113.42; https://finance.example.com; /panel-abc/');
});
test('IPv4 octets and command injection are rejected', () => {
  const { parseSettings } = api();
  for (const ip of ['256.1.1.1', '23.94.184.3; touch /tmp/oops', '$(whoami)', '1.2.3', '001.2.3.4']) {
    assert.throws(() => parseSettings(ip, 'finance.example.com', ''));
  }
});
test('hostname validation protects Caddy configuration and shell blocks', () => {
  const { parseSettings } = api();
  for (const domain of ['https://finance.example.com', 'finance.example.com\nadmin off', 'bad;command.com', '-bad.example.com', 'a'.repeat(64)+'.com']) {
    assert.throws(() => parseSettings('203.0.113.42', domain, ''));
  }
  assert.equal(parseSettings('203.0.113.42', 'FINANCE.EXAMPLE.COM', '').DOMAIN, 'finance.example.com');
});
test('panel path is optional and cannot inject a command or URL query', () => {
  const { parseSettings } = api();
  assert.equal(parseSettings('203.0.113.42', 'finance.example.com', '').PANEL_PATH, '/安装输出的WebBasePath/');
  assert.equal(parseSettings('203.0.113.42', 'finance.example.com', '/panel/abc/').PANEL_PATH, '/panel/abc/');
  for (const path of ['../etc', 'a?secret=b', 'x;sh', 'https://evil.example']) {
    assert.throws(() => parseSettings('203.0.113.42', 'finance.example.com', path));
  }
});

function commandContaining(marker) {
  const html = fs.readFileSync(file, 'utf8');
  const codes = [...html.matchAll(/<pre><code data-template>([\s\S]*?)<\/code><\/pre>/g)]
    .map(match => match[1].replace(/&quot;/g, '"').replace(/&#x27;/g, "'")
      .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'));
  const code = codes.find(value => value.includes(marker));
  assert.ok(code, 'command block missing: ' + marker);
  return code;
}
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'vps-guide-release-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, 'releases/known-good'), { recursive: true });
  fs.writeFileSync(path.join(root, 'releases/known-good/index.html'), 'known good');
  fs.symlinkSync(path.join(root, 'releases/known-good'), path.join(root, 'current'));
  const mv = path.join(root, 'mv.cjs');
  fs.writeFileSync(mv, "const fs=require('node:fs');const args=process.argv.slice(-2);fs.renameSync(args[0],args[1]);");
  return { root, mv };
}
function localize(code, f) {
  return code.split('/srv/www/finance').join(f.root)
    .replace('$(date -u +%Y%m%dT%H%M%SZ)', 'candidate')
    .replace(/^mv -Tf /gm, '"' + process.execPath + '" "' + f.mv + '" ');
}
test('failed extraction preserves the currently served release', t => {
  const f = fixture(t);
  const brokenTar = path.join(f.root, 'broken-tar.sh');
  fs.writeFileSync(brokenTar, '#!/bin/sh\nwhile [ "$1" != "-C" ]; do shift; done\nshift\n: > "$1/index.html"\n: > "$1/learn.rsc"\nexit 2\n');
  fs.chmodSync(brokenTar, 0o755);
  const code = localize(commandContaining('FINANCE_RELEASE='), f)
    .replace('tar -xzf ', '"' + brokenTar + '" -xzf ');
  const result = spawnSync('bash', ['-c', code], { encoding: 'utf8' });
  assert.notEqual(result.status, 0, 'failed tar must stop the block');
  assert.equal(fs.readlinkSync(path.join(f.root, 'current')), path.join(f.root, 'releases/known-good'));
});
test('an existing temporary link cannot silently replace the current release', t => {
  const f = fixture(t);
  fs.mkdirSync(path.join(f.root, 'stale-release'));
  fs.symlinkSync(path.join(f.root, 'stale-release'), path.join(f.root, 'current.next'));
  const archiveSource = path.join(f.root, 'archive-source');
  fs.mkdirSync(archiveSource);
  fs.writeFileSync(path.join(archiveSource, 'index.html'), 'candidate');
  fs.writeFileSync(path.join(archiveSource, 'learn.rsc'), 'candidate rsc');
  const archive = path.join(f.root, 'site.tar.gz');
  assert.equal(spawnSync('tar', ['-czf', archive, '-C', archiveSource, '.']).status, 0);
  const code = localize(commandContaining('FINANCE_RELEASE='), f)
    .replace('"$HOME/finance-site.tar.gz"', '"' + archive + '"');
  const result = spawnSync('bash', ['-c', code], { encoding: 'utf8' });
  assert.notEqual(result.status, 0, 'failed ln must stop the block');
  assert.equal(fs.readlinkSync(path.join(f.root, 'current')), path.join(f.root, 'releases/known-good'));
});
test('a missing rollback target leaves the current release intact', t => {
  const f = fixture(t);
  const code = localize(commandContaining('ln -s /srv/www/finance/releases/旧版本时间戳'), f);
  const result = spawnSync('bash', ['-c', code], { encoding: 'utf8' });
  assert.notEqual(result.status, 0, 'missing rollback target must stop the block');
  assert.equal(fs.readlinkSync(path.join(f.root, 'current')), path.join(f.root, 'releases/known-good'));
});
