# Single C++ Test File Task

Use this template when asking ChatGPT to generate one complete future C++ test file.

## Inputs To Attach

Attach or paste these project files:

```text
chatgpt-sources/cpp/project-contract.md
chatgpt-sources/cpp/example-test-file.cpp
```

Then generate a focused task document with one of:

```bash
python3 tools/cpp_render_task.py vector
python3 tools/cpp_render_task.py containers.vector_sequence
python3 tools/cpp_render_task.py std::vector::push_back
```

Prefer targets that resolve to `checklists/cpp/stdlib.tasks.json`; generated checklist item rendering is a fallback for APIs that do not have curated tasks yet.

## Rendered Task

```text
<paste tools/cpp_render_task.py output here>
```

## Output Instruction

Generate the complete content of the requested `languages/cpp/..._test.cpp` file.

Return only the file content. Do not return explanations, Markdown fences, or partial patches unless explicitly requested.

## Completion Reminder

After the example passes in this project, update the matching JSON task or checklist item:

- set `status` to `done`
- append the generated test file path to `test_files`
