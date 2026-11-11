import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import lint from '@commitlint/lint';
import conventional from '@commitlint/config-conventional';

const rules = { ...conventional.rules, 'subject-case': [0] };

async function checkMessage(message) {
  const report = await lint(message, rules, { defaultIgnores: false });
  if (!report.valid) throw new Error(report.errors.map(error => error.message).join('; '));
}

try {
  const { pull_request: pr } = JSON.parse(readFileSync(process.argv[2] || process.env.GITHUB_EVENT_PATH, 'utf8'));
  if (!pr || !/^[a-f0-9]{40}$/i.test(pr.base?.sha) || !/^[a-f0-9]{40}$/i.test(pr.head?.sha)) {
    throw new Error('A pull request event with base and head commit SHAs is required');
  }
  const title = pr.title.replace(/^\[[A-Z][A-Z0-9]*-[0-9]+\]\s+/, '');
  await checkMessage(title);
  const branch = pr.head.ref.match(/^(feat|fix|refactor|chore|docs|test|build|ci|perf|revert)\/(?:[A-Z][A-Z0-9]*-[0-9]+-)?[a-z0-9]+(?:-[a-z0-9]+)*$/);
  if (!branch || !title.startsWith(branch[1] + ': ') || pr.base.ref !== 'main') {
    throw new Error('Use a type/kebab-case branch, a matching PR type, and main as the base');
  }
  const body = (pr.body || '').replace(/\r\n/g, '\n').replace(/<!--[\s\S]*?-->/g, '');
  const sections = new Map(body.split(/^##[ \t]+/m).slice(1).map(block => {
    const end = block.indexOf('\n');
    return [block.slice(0, end).trim(), block.slice(end + 1).trim()];
  }));
  for (const name of ['Summary', 'Evidence', 'Merge Danger']) {
    if (!sections.get(name)) throw new Error(`${name} must contain a description`);
  }
  const evidence = sections.get('Evidence').match(/\*\*Before:\*\*([\s\S]*?)\*\*After:\*\*([\s\S]*)/);
  if (!evidence || !evidence[1].trim() || !evidence[2].trim()) {
    throw new Error('Evidence requires nonempty Before and After descriptions');
  }
  const danger = sections.get('Merge Danger');
  if (!/^\*\*Door:\*\*[ \t]+(?:one-way|two-way)[ \t]*$/m.test(danger)
      || !/^\*\*Blast Radius:\*\*[ \t]+[A-Za-z][^\n]*$/m.test(danger)) {
    throw new Error('Merge Danger requires Door: one-way/two-way and a Blast Radius');
  }
  const messages = execFileSync('git', ['log', '--no-merges', '--format=%B%x00', `${pr.base.sha}..${pr.head.sha}`], {
    encoding: 'utf8', maxBuffer: 8 * 1024 * 1024,
  }).split('\0').map(message => message.trim()).filter(Boolean);
  if (!messages.length) throw new Error('The pull request contains no new commits');
  for (const message of messages) await checkMessage(message);
  console.log(`PR policy passed for ${pr.head.sha}; checked ${messages.length} new commits`);
} catch (error) {
  console.error(`PR policy failed: ${error.message}`);
  process.exitCode = 1;
}
