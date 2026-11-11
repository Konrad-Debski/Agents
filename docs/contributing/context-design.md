# Sources and decisions for organizing knowledge

## The video and its conclusions

Source: Kyle Cook, Web Dev Simplified, [Why Your AI Generates Crap Code - And How to Fix It](https://www.youtube.com/watch?v=jojMVmRZABw). The analysis is based on the [full video transcript](https://transcriptly.libmap.cn/transcripts/jojMVmRZABw) and on the title and chapters confirmed in YouTube data. The visuals of the demos were not reviewed separately.

- From 00:45 Kyle separates the system prompt, instructions, skills, documentation and code. Every loaded piece of material takes up context.
- From 03:55 he shows the cost of long instructions, duplication and adding another rule after every mistake.
- From 07:23 he proposes short instructions with conditional links to topic documentation. A single large replacement file that is always read keeps the same problem.
- From 13:53 he covers a shared source for `AGENTS.md` and `CLAUDE.md` through a symlink, and from 15:50 instructions for selected parts of a project.
- From 18:47 he puts repeatable, specialized tasks in skills. Their names and descriptions also take up context, so the choice of skill set and short descriptions matter.

## Adopted solutions

- The main `AGENTS.md` holds only the knowledge map and the conditions for reading each source.
- Context7 has one procedure source. The style skill is chosen for writing tasks, without a forced read on every task.
- The documentation has `operations/`, `integrations/`, `contributing/` and `skills/` directories, split by type of work.
- Conditional Famicord data and the WordPress audit references sit next to the matching skills. Mandatory checks and publishing rules stay in the main procedures.
- The Ponytail and Matt Pocock sources are pinned as submodules. Selected whole directories are exposed through symlinks, keeping their dependencies and metadata. [upstream.md](../skills/upstream.md) describes the selection.
- The existing adapter, which runs after synchronization, exposes new skills to Claude Code. Tests cover adding a skill, updating a submodule, removing a link and protecting personal skills.

## Checking with real tasks

After an update, start a fresh harness session so the skill catalog and instructions do not come from the previous version. For a running Claude Code session you can also use the refresh described in [synchronization.md](../operations/synchronization.md).

During the next real tasks, check how sources get chosen. An API question should lead to Context7, a WP update to `wp-update`, and an instruction change to the knowledge organization rules. Task reports should not need the whole skill catalog loaded. This is an observation of model behavior, and file tests alone do not replace it.

Add more skills after you identify a missing procedure. The [context management rules](context-management.md) describe where to store new information.
