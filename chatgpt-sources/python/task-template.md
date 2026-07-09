# Single Python Test File Task

Use this template when asking ChatGPT to generate one complete future Python test file.

## Inputs To Attach

Attach or paste these project files:

```text
chatgpt-sources/project-instructions.md
chatgpt-sources/python/project-contract.md
chatgpt-sources/python/example-test-file.py
```

If `chatgpt-sources/project-instructions.md` is already installed as ChatGPT
Project Instructions, do not paste it again; use it as the controlling global
generation rule.

Then generate a focused task document with one of:

```bash
python3 tools/python_render_task.py heapq
python3 tools/python_render_task.py list.sort
python3 tools/python_render_task.py pathlib
```

Prefer targets that resolve to `checklists/python/stdlib.tasks.json`; old checklist item rendering is a fallback for APIs that do not have curated tasks yet.

## Rendered Task

```text
<paste tools/python_render_task.py output here>
```

## Output Instruction

Generate the complete content of the requested `languages/python/..._test.py` file.

Return only the file content. Do not return explanations, Markdown fences, or partial patches unless explicitly requested.

## Completion Reminder

After the test passes in this project, update the matching JSON task or checklist item:

- set `status` to `done`
- append the generated test file path to `test_files`
