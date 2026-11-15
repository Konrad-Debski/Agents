# Skill index

Use this map when the harness does not show the skill catalog. Open the procedure that matches the task. The mode below comes from the metadata, and its handling depends on the [harness](../integrations/README.md). Pointing to a file does not authorize publishing or deploying.

| Task | Skill | Mode | Output |
| --- | --- | --- | --- |
| Current documentation for libraries, SDKs, APIs, CLIs and cloud | [context7-mcp](../../skills/context7-mcp/SKILL.md) | Agent-selected | An answer or implementation based on the documentation |
| Editing text | [unslop](../../skills/unslop/SKILL.md) | Manual | Revised text |
| Writing a PR description | [pr](../../skills/pr/SKILL.md) | Agent-selected | A PR description |
| Publishing and merging a PR | [create-pr](../../skills/create-pr/SKILL.md) | Manual | A verified publishing result |
| Porting theme changes between companies | [famicord-sync](../../skills/famicord-sync/SKILL.md) | Agent-selected | Changes, validation and the status of each repository |
| WordPress/ACF section brief from Figma | [figma](../../skills/figma/SKILL.md) | Manual | A brief, no implementation |
| Analyzing a WordPress copy or SQL dump after a hack | [wp-audit](../../skills/wp-audit/SKILL.md) | Agent-selected | A report of evidence and analysis scope |
| Updating WordPress, plugins and ACF | [wp-update](../../skills/wp-update/SKILL.md) | Agent-selected | Versions, validation and publishing status |
| Inspecting a WordPress repository before changes | [wp-project-triage](../../skills/wp-project-triage/SKILL.md) | Agent-selected | A JSON report of project kind, tooling and tests |
| Configuring or fixing PHPStan in a WordPress project | [wp-phpstan](../../skills/wp-phpstan/SKILL.md) | Agent-selected | PHPStan configuration, stubs and fixes |
| Investigating WordPress backend performance | [wp-performance](../../skills/wp-performance/SKILL.md) | Agent-selected | Measurements, causes and verified fixes |
| Formatting pasted update notices | [wp-update-list](../../skills/wp-update-list/SKILL.md) | Agent-selected | A version list, no project update |
| Refining a plan | [grill-me](../../skills/grill-me/SKILL.md) | Manual | An interview following [grilling](../../skills/grilling/SKILL.md) |
| Writing instructions for agents | [writing-for-agents](../../skills/writing-for-agents/SKILL.md) | Agent-selected | Instructions and read conditions |
| Diagnosing a bug or performance regression | [diagnosing-bugs](../../skills/diagnosing-bugs/SKILL.md) | Agent-selected | A confirmed cause and a verified fix |
| Retrospective of a coding session | [retro](../../skills/retro/SKILL.md) | Manual | Proposed improvements to the agent environment |
| Handing work off to the next session | [handoff](../../skills/handoff/SKILL.md) | Manual | A handoff document in a temporary directory |
| Implementing or fixing with TDD | [tdd](../../skills/tdd/SKILL.md) | Agent-selected | Behavior verified by a test written before the implementation |
| Designing interfaces and improving testability | [codebase-design](../../skills/codebase-design/SKILL.md) | Agent-selected | Module design rules |
| Implementing with existing patterns | [ponytail](../../skills/ponytail/SKILL.md) | Agent-selected | A small, complete change |
| Reviewing correctness and unneeded code | [ponytail-review](../../skills/ponytail-review/SKILL.md) | Agent-selected | A review report, no code changes |
| Auditing a whole repository | [ponytail-audit](../../skills/ponytail-audit/SKILL.md) | Agent-selected | A report of bugs, risks and unneeded code, no code changes |

## Shared references

`wp-update` and `famicord-sync` read the [publishing protocol](../../skills/create-pr/references/workflow.md) only right before that phase. This is a document read, without invoking the manual `create-pr`. For links to the style rules in the global map, also read the linked file as a reference.

`pr` reads the publishing protocol when preparing a description. `pr` owns the description content, and the protocol owns publishing and merging. Writing a description alone does not authorize those operations.

`grill-me` requires `grilling`. In a harness without a `Skill` tool, read both files. Installing the skill alone does not start the interview.

`wp-phpstan` uses the `wp-project-triage` report. The WordPress skills give script paths relative to the upstream repository; [upstream.md](upstream.md) describes how to resolve them.

`retro` uses `writing-for-agents`, and `tdd` uses `codebase-design` when an interface needs designing for tests. Whole-directory symlinks keep the TDD and module design references. `tdd` refers to `code-review` when discussing the review stage. That skill stays upstream, and the separately available `ponytail-review` has its own procedure.

The `tdd` and `codebase-design` descriptions are enough for agent selection. `retro` and `handoff` keep the manual invocation mode. Their map stays in this index, with no extra entries in the global `AGENTS.md`.

[upstream.md](upstream.md) describes source selection, dependencies and updates.
