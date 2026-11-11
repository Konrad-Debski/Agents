# Organizing knowledge for agents

Load when changing instructions, skills or documentation in `~/.agents`.

## Where to store knowledge

| Content | Location |
| --- | --- |
| Read condition and source pointer | The main `AGENTS.md` |
| Configuration, conventions and maintenance | A topic file in `docs/` |
| A coherent procedure for a specific task | `skills/<name>/SKILL.md` |
| Details needed only in a specific variant | `skills/<name>/references/` |
| A protocol shared by several procedures | One Markdown reference that every consumer points to |
| Knowledge about a single project | That project's instructions, documentation or skills |

## Content and read conditions

- The main `AGENTS.md` stays a map. Each link names a topic and a read condition. Open only the sources the task needs.
- Keep coherent units of work. Split out variants and long references when they are not needed on every use. A short skill can stay a single file.
- Each rule has one source. Read shared protocols as files, without invoking manual skills as dependencies. Keep the existing skill invocation mode and required approvals.
- A skill description states the user intent and the boundary against similar tasks. Steps, commands and the output format belong in the body or references.
- Keep relevant environment exceptions, authorization limits and checkable completion criteria. Remove repetition and general advice that does not change the agent's decisions.

## Language

Write every Markdown file in this repository in English: `AGENTS.md`, `README.md`, `docs/`, skills and their references. Keep the original language of input data, quoted examples and fixed messages a procedure requires, such as the Polish client message in `famicord-sync`. Keep one copy of each procedure, with no translations of it elsewhere.

## Sources and maintenance

The editing is based on the [For skill creators series](https://agentskills.io/skill-creation/best-practices):

- [Quickstart](https://agentskills.io/skill-creation/quickstart): minimal structure and skill discovery.
- [Best practices](https://agentskills.io/skill-creation/best-practices): domain knowledge, scope and conditional references.
- [Optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions): selection by intent and telling similar requests apart.
- [Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills): judging the results and the course of real tasks.
- [Using scripts](https://agentskills.io/skill-creation/using-scripts): automating repeated work when usage justifies it.

Change instructions based on an identified problem. A shorter text or valid frontmatter alone does not prove better behavior. Future evaluations should cover both skill selection and output quality. Add automation only for repeated work.

External sources are submodules pinned to approved versions. Update their gitlinks through a pull request; the timer distributes only merged versions. Do not edit upstream files. [upstream.md](../skills/upstream.md) describes their selection, and [synchronization.md](../operations/synchronization.md) the update rules.

## Paths

The global map uses `~/.agents/...` because symlinks expose it outside the repository. Expand `~` to the current home directory. In documents and skills, use links relative to the file.

A file you have already read stays in the conversation context. The split limits future reads. Handling of the skill catalog, metadata and refreshes depends on the [harness](../integrations/README.md).
