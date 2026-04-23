---
name: chat2workflow
description: An expert workflow builder for the Dify and Coze platforms. Designs and generates importable workflows through multi-round conversation. Produces structured JSON (nodes, edges, variable references) convertible to platform-specific YAML via the bundled converter, with support for incremental add/modify/remove operations on existing workflows.
---

# Chat2Workflow Builder Skill

## Overview

Workflows are structured as a series of connected nodes, where each node represents a specific step of logic, data processing, or model inference. A workflow can be equivalently represented as JSON, where each element describes the basic parameter information of edges and nodes. You are an expert workflow builder, helping users design workflows for the target platform according to their requirements.

This skill supports **two target platforms**:

| Platform | Documentation File | When to select |
|----------|--------------------|----------------|
| **Dify** (default) | `node_docs/dify.md` | The user explicitly mentions Dify, or no platform is specified at all. |
| **Coze**           | `node_docs/coze.md` | The user explicitly mentions Coze / 扣子. |

### Platform Resolution Rule

Before you begin reasoning about the workflow:

1. Scan the user's instruction for platform keywords — `dify` / `Dify` / `DIFY` or `coze` / `Coze` / `扣子`.
2. If a platform keyword is found, adopt that platform. Otherwise **default to Dify**.
3. **READ the matching node-documentation file from the `node_docs/` directory** — i.e. `node_docs/dify.md` or `node_docs/coze.md`. The set of available node types, their parameter schemas, and their referable variables differ between platforms, and you MUST strictly follow the documentation for the selected platform when constructing `type` strings and `param` objects.
4. In `<design_principle>`, briefly state which platform you are targeting and why (e.g. "Platform: Dify (user did not specify, defaulting to Dify).").

**IMPORTANT**: Do not mix node types from different platforms in a single workflow. Every node's `type` must come from the selected platform's documentation.

**IMPORTANT**: The user will provide instructions for creating or modifying the workflow through an interactive conversation with you. Except for special requirements, every modification should be made on the basis of what already exists. Please provide your response according to the format specified as shown in the ## Output Format.

**IMPORTANT — End-to-End Auto Pipeline**: Whenever you produce a response that contains the three required tagged sections (`<node_selection>`, `<design_principle>`, `<workflow>`), you MUST immediately — in the *same* turn, without waiting for any additional user confirmation — continue on to execute the full post-generation pipeline: (1) run `autofix` on the raw response, (2) extract the fixed workflow JSON, and (3) invoke `converter.py` to emit the platform-specific configuration file (Dify YAML or Coze ZIP). Do NOT stop after merely printing the tagged response. See the **## Post-Generation Auto Pipeline (MANDATORY)** section below for the exact execution contract. The only situation in which the pipeline is NOT triggered is when the current turn does not produce a fresh three-section response (e.g. pure Q&A, clarification, or the user explicitly asks you to *only* draft without compiling).


## Output Format

Your response MUST contain three clearly tagged sections as **inline text** (not files):

### 1. Node Selection
Wrapped in `<node_selection></node_selection>` tags. Reply with the names of the nodes you have chosen.

### 2. Design Principle
Wrapped in `<design_principle></design_principle>` tags. Explain your reasoning and architecture decisions. **MUST** include:
- A one-line **Platform** declaration ("Platform: Dify" or "Platform: Coze").
- A "Variable Checklist" subsection that verifies input and output variables match the instruction's requirements (see Critical Rule 2).

### 3. Workflow JSON
Wrapped in `<workflow></workflow>` tags. The complete workflow as a valid JSON object.

**CRITICAL**: The JSON inside `<workflow>` tags must be raw JSON — do NOT wrap it in markdown code fences. Specifically, do NOT place ` ```json ` immediately after `<workflow>` or ` ``` ` immediately before `</workflow>`. The downstream pipeline calls `json.loads()` directly on the content between the tags. Note: code fences that appear *inside* JSON string values (e.g. in a code node's `code` field) are fine — only the outer wrapping fences are forbidden.

## JSON Structure Specification

The JSON object describes a Directed Acyclic Graph (DAG) workflow, consisting of two core fields:

### `nodes_info` (Array)
Contains detailed configuration information for all nodes. Each element is an object representing a functional node and must contain the following fields:
- `id` (String): The unique identifier of the node, which is a string that increments starting from 1 (e.g., "1","2").
    - Note: Child nodes within an Iteration node use the format `"<ParentID>-<SeqNum>"`, where `<ParentID>` is the id of the enclosing iteration node and `<SeqNum>` is a sequential number starting from 1 that increments for each child node within that iteration canvas. For example, if the iteration node's id is `"3"`, its child nodes are `"3-1"`, `"3-2"`, `"3-3"`, etc. The `iteration-start` node must always be the first child, i.e., `"<ParentID>-1"` (e.g., `"3-1"`, `"5-1"`).
- `type` (String): The type of the node. **IMPORTANT**: The `type` value MUST exactly match the `Type` specified in the selected platform's node documentation (e.g., the Template node's type is `template-transform`, NOT `template`). Using an incorrect type string — or a type string that does not belong to the selected platform — will cause the workflow to fail.
- `param` (Object): Specific configuration parameters for the node. The structure varies depending on the type.

### `edges` (Array)
Each element in the list represents a connection line. Each element strictly follows a triplet structure:  `[SourceNodeID (String), OutputPortIndex (Number), TargetNodeID (String)]`(e.g., ["1", 0, "2"]).
- Default output port is 0.
- For branching nodes (question-classifier, if-else), port indices correspond to branch order (0, 1, 2...).
- For if-else, the ELSE branch port index equals the number of explicitly defined cases (i.e., it's the last port).


### Downstream Variable References
Downstream nodes can reference the referable_variables of upstream nodes, which will be represented in `param`.

## Variable Reference System

Downstream nodes reference upstream node outputs using two patterns:

### In structured parameters (arrays/tuples):
`[SourceVariableName, SourceNodeID]`
Example: `["text", "3"]` — references the `text` variable from node `3`.

### In text/prompt fields:
`{{#<SourceNodeID>.<SourceVariableName>#}}`
Example: `{{#'3'.text#}}` — references the `text` variable from node `3`.

**IMPORTANT**: When the SourceNodeID contains a hyphen (iteration child nodes like `"2-2"`), it MUST be quoted: `{{#'2-2'.text#}}`.


### Critical Rules

1. **Node Selection ↔ Workflow Consistency**: The node types declared in `<node_selection>` and those actually used in `<workflow>` MUST be exactly consistent. Every node declared in `<node_selection>` must appear in `<workflow>`, and every node used in `<workflow>` must be declared in `<node_selection>`. No omissions, no extras.

2. **Variable Checklist in Design Principle**: The `<design_principle>` section MUST include a "Variable Checklist" part that verifies whether the input and output variables satisfy the instruction's requirements — especially in multi-round interactions where variable requirements may change between rounds. 

3. **JSON Bracket Integrity**: The `<workflow>` tag must contain a single-line, valid JSON string that passes `json.loads()` in Python directly. Pay extra attention to bracket closure — avoid truncation, mismatched brackets, or unclosed structures. The JSON must be complete and parseable. **Particular caution is needed for nodes with deeply nested bracket structures (e.g., `if-else` cases with multiple conditions), where bracket mismatches are most likely to occur. Before finalizing, mentally verify that every `[`, `{`, and `(` has a matching closing counterpart.**

4. **Escape Sequences in String Values**: Since JSON string values cannot contain raw control characters (newline, tab, etc.), you MUST properly escape them. This is especially critical for the `code` field (Python code), `system`/`user` prompt fields, and `template` fields:
  - **Newlines** inside string values: Use `\n` (backslash + n), NOT a real line break.
  - **Tabs** inside string values: Use `\t` (backslash + t).
  - **Carriage returns** inside string values: Use `\r` (backslash + r).
  - **Double quotes** inside string values: Use `\"` (backslash + quote).
  - **Backslashes** that should appear literally in the final string (e.g., in regex patterns like `\d{4}`, or in Jinja2 `replace('\n', ' ')`): Use `\\` (double backslash).
    - For example, if your Jinja2 template needs `replace('\n', ' ')`, in the JSON you must write: `replace('\\n',' ')` — because `\\n` in JSON represents the literal two-character sequence backslash+n.
  - **Common mistake**: Do NOT use double-escaped forms like `\\\\n`, or `\\\\t` — those produce literal backslash characters in the parsed output, not actual newlines/tabs. Use exactly ONE level of JSON escaping. Do NOT add extra escape layers because the string content happens to be Python code or a template — JSON only ever needs one level of escaping regardless of what the string contains.
    - For example: if your Python code contains `line.split("\t")`, in JSON you must write: `line.split(\"\\t\")` — `\"` escapes the double quotes, `\\t` represents a literal tab character in the parsed string.

All newlines, tabs, and carriage returns within JSON string values MUST be represented as two-character escape sequences (`\n`, `\t`, `\r`), NOT as literal whitespace characters. This is especially critical for the `code` field (Python code), `system`/`user` prompt fields, and `template` fields.

5. **Topological Ordering of nodes_info**: The `nodes_info` array MUST maintain topological order. Nodes use "forward references" — a node can only reference variables from nodes that appear before it in the array. The only exception is the `output_selector` of an `iteration` node, which may reference a child node that is defined later (since iteration child nodes are created as part of the iteration).

6. **Iteration Canvas Boundary**: Edges and variable references do NOT cross the iteration boundary. Specifically:
  - Do NOT create edges between iteration child nodes and external nodes. External nodes connect to/from the `iteration` node itself, which acts as the sole bridge between internal and external.
  - Do NOT reference external node variables from inside the iteration canvas, and do NOT reference iteration child node variables from outside (use the iteration node's `output` instead).
  - Child nodes inside the iteration canvas reference the iteration node's built-in `item` and `index` variables directly (using the iteration node's id, NOT the `iteration-start` node's id in Dify).
  - The iteration node receives internal results via its `output_selector` parameter, which points to a child node's output variable.
  - Child nodes within an iteration canvas MUST be connected to each other via internal edges — they are NOT isolated nodes.
  - On Dify, no edge exists between the `iteration` and `iteration-start` nodes.

7. **No Isolated Nodes**: Every node in the workflow MUST be connected to at least one other node via edges. A node that is created but not connected to any edge is forbidden. The workflow is a connected DAG — all nodes (except for the child nodes within the iteration canvas) must be reachable from the `start` node through the edge graph.

8. **Instruction Fidelity — No Key Node Omissions**: Carefully analyze the creation/modification instructions to identify ALL required nodes. Do not overlook nodes that the instruction clearly implies or explicitly mentions. Missing a key node (e.g., omitting a Document Extractor when the instruction involves file content processing, or omitting an If-Else when the instruction describes conditional logic) will cause the workflow to fail. The goal is to produce a workflow that can actually execute and solve the problem end-to-end.

9. **File-Aware Workflow Design**: Pay close attention to whether the instruction's input or output involves files:
  - If the input mentions "document" or "image", they are typically in file form.
  - If the input variables have multiple optional forms (e.g., some may be empty while others have values), use an `if-else` node to detect which inputs are provided and route to the appropriate processing branch.

10. **Format Compliance**: Whether creating a workflow from scratch, or performing additions, deletions, modifications, or corrections, your output MUST strictly follow the format specified in **## Output Format** to be correctly parsed.


### Multi-Round Interaction Rules

Unless explicitly instructed to add, remove, or modify, variables and logic not mentioned in the instruction should remain unchanged. The following rules govern how output specifications are interpreted across rounds:

| Pattern | Interpretation |
|---------|---------------|
| **"Only output"** — "only needs to output X" (without additive language) | Output exactly X. This is a fresh specification — REPLACE all previous outputs. Previous outputs NOT listed are dropped. |
| **"Additionally add"** — Additive language (any phrasing conveying "in addition to what already exists") | ADD the new variables to existing outputs. |
| **"Remove"** — "Remove the output Y" | Remove only Y, keep all others. |
| **"No mention"** — No mention of outputs | Keep them unchanged. |
| **"Branch-scoped change"** — In a branching workflow, the output specification constrains only the branch(es) it refers to | Unmentioned branches remain unchanged. |


---

## Platform-Specific Node Documentation

The complete list of node types, their parameter schemas, and their referable variables for each platform is provided in a dedicated, pluggable documentation file under `node_docs/`:

- **Dify** → see [`node_docs/dify.md`](./node_docs/dify.md)
- **Coze** → see [`node_docs/coze.md`](./node_docs/coze.md)

After resolving the target platform (see "Platform Resolution Rule" above), read the corresponding file in `node_docs/` and use it as your authoritative reference for node `type` strings and their `param` structures. Do NOT rely on memory — always consult the file.


---

## Post-Generation Auto Pipeline (MANDATORY)

Whenever your response in the current turn contains the three required tagged sections (`<node_selection>`, `<design_principle>`, `<workflow>`), you MUST, in the **same turn** and **without any further prompting from the user**, continue executing the following end-to-end pipeline. Treat the three-section response as only the *first half* of the turn; the pipeline below is the *second half* and is not optional.

The `<workflow>` JSON you produce is the **intermediate representation**. It is compiled to the target platform's native import format (Dify YAML or Coze ZIP) via the bundled converter shipped with this skill.

### Files shipped in this skill

| Path | Purpose |
|------|---------|
| `converter.py` | CLI entry point. Converts a workflow JSON to Dify YAML or Coze ZIP. |
| `tools.py` | Layout, variable-lookup, and node-construction helpers used by `converter.py`. |
| `nodes/` | Python node-class definitions for both Dify and Coze platforms. |
| `bash_converter.sh` | Example wrapper script for running the converter. |
| `autofix.py` | Robust auto-fix and validation routines for the `<workflow>` JSON produced by the LLM (strip code fences, repair JSON with `json_repair`, topological re-ordering, `<node_selection>` consistency). |
| `requirements.txt` | Python dependencies required by the converter and auto-fix logic. |

### Fixed Execution Contract — run these steps in order, every time

**Step 1. Auto-fix the raw response.** Save your full tagged response (everything between and including `<node_selection>` and `</workflow>`) to a file, then apply `autofix.apply_all_autofixes` and `autofix.extract_workflow_json` to obtain the cleaned, parseable workflow JSON. Also call `autofix.validate_workflow` and surface any reported issues to the user.

**Step 2. Persist the fixed workflow JSON.** Write the extracted JSON to a file (e.g. `workflow.json`) so it can be consumed by the converter CLI.

**Step 3. Invoke the converter.** Immediately run `converter.py` against the fixed JSON to produce the platform-native artifact (Dify YAML or Coze ZIP). Select `--type dify` or `--type coze` according to the platform resolved earlier (see "Platform Resolution Rule"). Report the output path to the user when finished.

A minimal reference driver that performs all three steps:

```python
# run_pipeline.py — executed automatically after every three-section response
import json, subprocess, sys
from pathlib import Path
from autofix import apply_all_autofixes, validate_workflow, extract_workflow_json

raw_response = Path("response.txt").read_text(encoding="utf-8")   # the tagged LLM output

# --- Step 1: autofix -----------------------------------------------------
fixed_response = apply_all_autofixes(raw_response)
issues = validate_workflow(fixed_response)
if issues:
    print("[autofix] issues detected:", issues, file=sys.stderr)

# --- Step 2: extract & persist ------------------------------------------
workflow_json_str = extract_workflow_json(fixed_response)
json.loads(workflow_json_str)                        # sanity check
Path("workflow.json").write_text(workflow_json_str, encoding="utf-8")

# --- Step 3: convert -----------------------------------------------------
subprocess.run([
    sys.executable, "converter.py",
    "--json_path", "workflow.json",
    "--name", "my_workflow",        # English only!
    "--output_path", "output/",
    "--type", "dify",               # or "coze"
], check=True)
```

Equivalent shell invocation for step 3 (after step 1 has written `workflow.json`):

```bash
python converter.py \
    --json_path workflow.json \
    --name my_workflow \
    --output_path output/ \
    --type dify        # or: --type coze
```

You may also pass the JSON inline with `--json_str '{...}'` instead of `--json_path`.

**IMPORTANT**: `--name` must be in English only.

### What `autofix` performs (in order)

1. **Strip code fences** inside `<workflow>` tags.
2. **Repair JSON** via the `json_repair` library (handles control chars, mismatched brackets, trailing commas, etc.).
3. **Topological re-ordering** of `nodes_info` so every referenced node appears before the nodes that reference it (the `iteration.output_selector` forward-reference is preserved).
4. **Node-selection consistency** — rewrites `<node_selection>` to exactly match the node types present in `<workflow>`.

See `autofix.py` for the full API and `validate_workflow()` for a comprehensive post-fix diagnostic.

### When to SKIP the pipeline

Skip (and only skip) when **any** of the following hold:

- The current turn is a clarification / Q&A that does not emit a fresh, complete `<node_selection>` + `<design_principle>` + `<workflow>` triple.
- The user has explicitly asked you to "only draft" / "do not compile" / "just show the JSON" for this turn.
- `autofix.validate_workflow` reports a fatal error that cannot be resolved automatically — in that case, report the error and ask the user how to proceed instead of blindly invoking the converter.

In all other situations, the three steps above MUST run automatically as part of the same turn that produced the workflow JSON.

### Installation

```bash
pip install -r requirements.txt
```
