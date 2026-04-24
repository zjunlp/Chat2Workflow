# Converter Utility — Manual CLI Usage

This document is **not part of the `chat2workflow` skill's runtime** and is
not referenced by `SKILL.md`. It describes the optional, standalone
command-line utilities shipped in this folder — `converter.py`, `autofix.py`,
`tools.py`, and `bash_converter.sh` — for users who want to compile a
workflow JSON (produced separately by the skill's text output) into a
Dify YAML file or a Coze ZIP bundle on their own machine.

The skill's own deliverable is purely text (the three tagged sections). These
utilities are read-and-write file tools that a user runs manually from a
shell; nothing about using the skill requires running them.

For an independent safety audit of the utilities' imports and behavior (no
network I/O, no shell execution, no credential access), see
[`SAFETY_AUDIT.md`](./SAFETY_AUDIT.md).

---

## 1. Prerequisites

Two third-party Python packages are required. They are listed in
`requirements.txt` and can be installed with whichever Python package
manager the user prefers:

- `PyYAML` — emits Dify YAML.
- `json_repair` — used by the offline auto-fix pass.

The utilities do not shell out to `pip`, `conda`, or any other package
manager. They run against whatever interpreter already has the packages
available.

## 2. CLI

```bash
python converter.py \
    --json_path ../workflow.json \
    --name my_workflow \
    --output_path ../chat2workflow_output/ \
    --type dify        # or: --type coze
```

Alternative flags:

- `--json_str '{...}'` — pass the workflow JSON inline instead of from a file.
- `--name` — name of the produced artifact. English only.
- `--output_path` — destination directory. When omitted, defaults to the
  sibling directory `../chat2workflow_output/` next to this folder.

A bash wrapper is also provided for convenience:

```bash
bash bash_converter.sh ../workflow.json my_workflow ../chat2workflow_output dify
```

## 3. Output-path policy

- Output is written under `--output_path`.
- If `--output_path` resolves **inside** this folder, `converter.py`
  redirects the write to `../chat2workflow_output/` instead, so the folder
  that ships the utilities is never written to.
- For Coze ZIPs, intermediate files during bundle assembly are placed in
  the system temp directory via `tempfile.mkdtemp()` and are removed once
  the final ZIP is emitted.
- `converter.py` sets `sys.dont_write_bytecode = True` before importing
  sibling modules, so no `__pycache__/` or `*.pyc` files are produced next
  to the source while running it.

## 4. `autofix.py` (optional pre-processing)

If the workflow JSON was taken directly from an LLM's tagged response and
has not been cleaned yet, the auto-fix pass can be run first:

1. Strip code fences inside `<workflow>` tags.
2. Repair JSON via `json_repair` (control chars, mismatched brackets,
   trailing commas, etc.).
3. Topologically re-order `nodes_info`, preserving the
   `iteration.output_selector` forward-reference.
4. Rewrite `<node_selection>` so that it exactly matches the node types
   actually used in `<workflow>`.

See `autofix.py` for the full API (`apply_all_autofixes`,
`extract_workflow_json`, `validate_workflow`).
