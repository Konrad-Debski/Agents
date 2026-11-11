import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';

const policy = resolve('scripts/quality/pr-policy.mjs');
const body = `## Summary
Preserve private configuration comments when removing a managed server.
## Evidence
**Before:** Removing the final server deleted a private comment.
**After:** The regression test preserves the comment.
## Merge Danger
**Door:** two-way
**Blast Radius:** configuration
`;

function fixture(t, message = 'fix: preserve private comments') {
  const directory = mkdtempSync(join(tmpdir(), 'agents-pr-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const env = { ...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1' };
  const git = (...args) => execFileSync('git', args, { cwd: directory, env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  git('init', '--initial-branch=main');
  git('config', 'user.name', 'PR test');
  git('config', 'user.email', 'pr@example.invalid');
  git('config', 'commit.gpgsign', 'false');
  git('commit', '--allow-empty', '-m', 'Legacy base message');
  const base = git('rev-parse', 'HEAD');
  git('switch', '-c', 'fix/private-comments');
  git('commit', '--allow-empty', '-m', message);
  const event = { pull_request: {
    title: 'fix: Preserve Private Comments', body,
    base: { sha: base, ref: 'main' },
    head: { sha: git('rev-parse', 'HEAD'), ref: 'fix/private-comments' },
  } };
  return { event, git, directory, run() {
    writeFileSync(join(directory, 'event.json'), JSON.stringify(event));
    return spawnSync(process.execPath, [policy, join(directory, 'event.json')], { cwd: directory, env, encoding: 'utf8' });
  } };
}

test('a valid PR checks its new commits without linting legacy history', (t) => {
  const result = fixture(t).run();
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

test('a PR with an empty description is rejected', (t) => {
  const f = fixture(t);
  f.event.pull_request.body = '';
  const result = f.run();
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Summary/);
});

test('the risk section must state reversibility and affected scope', (t) => {
  const f = fixture(t);
  f.event.pull_request.body = body.replace('**Door:** two-way', '**Door:** <!-- choose one -->');
  const result = f.run();
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Door/);
});

test('evidence must describe both the previous and resulting behavior', (t) => {
  const f = fixture(t);
  f.event.pull_request.body = body.replace('**Before:** Removing the final server deleted a private comment.', '**Before:** <!-- explain -->');
  const result = f.run();
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Before/);
});

test('the PR type must agree with the working branch', (t) => {
  const f = fixture(t);
  f.event.pull_request.title = 'feat: Preserve Private Comments';
  const result = f.run();
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /branch/);
});

test('a one-parent commit cannot bypass lint by pretending to be a merge', (t) => {
  const result = fixture(t, "Merge branch 'main'").run();
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /type|subject/);
});

test('ticket prefixes and real merge commits remain supported', (t) => {
  const f = fixture(t);
  f.git('switch', '-c', 'side');
  f.git('commit', '--allow-empty', '-m', 'test: exercise private configuration');
  f.git('switch', 'fix/private-comments');
  f.git('merge', '--no-ff', 'side', '-m', "Merge branch 'side'");
  f.event.pull_request.head.sha = f.git('rev-parse', 'HEAD');
  f.event.pull_request.head.ref = 'fix/ALTER-65-private-comments';
  f.event.pull_request.title = '[ALTER-65] fix: Preserve Private Comments';
  const result = f.run();
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

test('invalid commits block a PR even when its title is valid', (t) => {
  const result = fixture(t, 'Forgot the commit type').run();
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /type/);
});

test('PR text is data and cannot execute shell commands', (t) => {
  const f = fixture(t);
  f.event.pull_request.title = 'fix: Keep $(touch injected) literal';
  const result = f.run();
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.throws(() => readFileSync(join(f.directory, 'injected')), /ENOENT/);
});
