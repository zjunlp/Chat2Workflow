---
name: chat2workflow
description: A design-only workflow designer for the Dify and Coze platforms. Through multi-round conversation, it produces a structured workflow JSON (nodes, edges, variable references) as text output. The skill itself produces only text and never runs any scripts.
---

# Chat2Workflow Builder Skill

## What this skill does

This skill is **design-only**. Its deliverable is three tagged sections of text (see *Output Format* below) — most importantly a workflow JSON wrapped in `<workflow></workflow>`. Producing those three sections involves only reading the platform documentation under `node_docs/` and emitting text; nothing else happens.

A few Python files also live in this folder (`converter.py`, `autofix.py`, `tools.py`, `bash_converter.sh`). They are **not part of the skill's deliverable** and are not referenced by the generation process. They exist as standalone utilities that a user can run manually from a shell, entirely outside the skill's text-generation flow, if they separately want to turn a JSON file into a Dify YAML or Coze ZIP on their own machine. See the bundled `README`/source of those scripts for their CLI usage; the skill itself does not invoke them.

## Overview

A Chat2Workflow design is a Directed Acyclic Graph of connected nodes, where each node represents a step of logic, data processing, or model inference. The design is serialized as a JSON object that enumerates the nodes and the edges that connect them.

This skill supports **two target platforms**:

| Platform | Documentation File | Selection criterion |
|----------|--------------------|----------------|
| **Dify** (default) | `node_docs/dify.md` | The user instruction explicitly mentions Dify, or no platform is specified at all. |
| **Coze**           | `node_docs/coze.md` | The user instruction explicitly mentions Coze / 扣子. |

### Platform Resolution

Platform selection is a two-step lookup performed against the user's instruction:

1. The user's instruction is scanned for platform keywords — `dify` / `Dify` / `DIFY` or `coze` / `Coze` / `扣子`.
2. If a platform keyword is present, that platform is the target. Otherwise the target is Dify (the default).
3. The matching file from `node_docs/` — `node_docs/dify.md` or `node_docs/coze.md` — is the authoritative schema for node `type` strings, `param` objects, and referable variables on that platform. The two platforms have different node sets, different parameter schemas, and different referable variables.
4. The chosen platform is named in `<design_principle>` with a short justification, e.g. `"Platform: Dify (user did not specify, defaulting to Dify)."`.

A single workflow targets a single platform; every node's `type` comes from that platform's documentation file.

The interaction model is conversational: the user supplies creation or modification instructions across multiple rounds, and — unless an instruction says otherwise — each new response extends the current design rather than replacing it. Responses follow the structure described in *Output Format*.


## Output Format

A well-formed response consists of three clearly tagged sections rendered as **inline text** (not files):

### 1. Node Selection
Wrapped in `<node_selection></node_selection>` tags. Lists the names of the nodes chosen for the design.

### 2. Design Principle
Wrapped in `<design_principle></design_principle>` tags. Explains the reasoning and architecture decisions. Contains at minimum:
- A one-line **Platform** declaration (`Platform: Dify` or `Platform: Coze`).
- A `Variable Checklist` subsection that cross-checks the input and output variables against the instruction's requirements (see Workflow Validity Rule 2 below).

### 3. Workflow JSON
Wrapped in `<workflow></workflow>` tags. Contains the complete workflow as a single valid JSON object.

The content inside `<workflow>` is raw JSON — markdown code fences around it break parsing, because the downstream pipeline calls `json.loads()` directly on the content between the tags. Concretely, ` ```json ` immediately after `<workflow>` or ` ``` ` immediately before `</workflow>` will cause the parse step to fail. Code fences that appear *inside* JSON string values (for example inside a code node's `code` field) are fine — only the outer wrapping fences cause parsing problems.

## JSON Structure Specification

The JSON object describes a Directed Acyclic Graph (DAG) workflow, consisting of two core fields:

### `nodes_info` (Array)
Contains detailed configuration information for all nodes. Each element is an object representing a functional node and contains the following fields:
- `id` (String): The unique identifier of the node, a string that increments starting from 1 (e.g., "1","2").
    - Note: Child nodes within an Iteration node use the format `"<ParentID>-<SeqNum>"`, where `<ParentID>` is the id of the enclosing iteration node and `<SeqNum>` is a sequential number starting from 1 that increments for each child node within that iteration canvas. For example, if the iteration node's id is `"3"`, its child nodes are `"3-1"`, `"3-2"`, `"3-3"`, etc. The `iteration-start` node is always the first child, i.e., `"<ParentID>-1"` (e.g., `"3-1"`, `"5-1"`).
- `type` (String): The type of the node. The `type` value should exactly match the `Type` specified in the selected platform's node documentation (e.g., the Template node's type is `template-transform`, not `template`). Using an incorrect type string — or a type string that does not belong to the selected platform — will cause the workflow to fail.
- `param` (Object): Specific configuration parameters for the node. The structure varies depending on the type.

### `edges` (Array)
Each element in the list represents a connection line. Each element follows a triplet structure:  `[SourceNodeID (String), OutputPortIndex (Number), TargetNodeID (String)]`(e.g., ["1", 0, "2"]).
- Default output port is 0.
- For branching nodes (question-classifier, if-else), port indices correspond to branch order (0, 1, 2...).
- For if-else, the ELSE branch port index equals the number of explicitly defined cases (i.e., it's the last port).


### Downstream Variable References
Downstream nodes can reference the referable_variables of upstream nodes, which will be represented in `param`.

## Variable Reference System

Downstream nodes reference upstream node outputs through one of two patterns:

### In structured parameters (arrays/tuples):
`[SourceVariableName, SourceNodeID]`
Example: `["text", "3"]` — references the `text` variable from node `3`.

### In text fields:
`{{#<SourceNodeID>.<SourceVariableName>#}}`
Example: `{{#'3'.text#}}` — references the `text` variable from node `3`.

When the SourceNodeID contains a hyphen (iteration child nodes such as `"2-2"`), it is quoted: `{{#'2-2'.text#}}`.


### Workflow Validity Rules

The rules below describe what makes a produced workflow valid. They are constraints on the emitted JSON/tags, not instructions to any external system.

1. **Node Selection ↔ Workflow Consistency**: The node types declared in `<node_selection>` and those actually used in `<workflow>` are exactly consistent. Every node declared in `<node_selection>` appears in `<workflow>`, and every node used in `<workflow>` is declared in `<node_selection>`. No omissions, no extras.

2. **Variable Checklist in Design Principle**: The `<design_principle>` section contains a `Variable Checklist` subsection that verifies whether the input and output variables satisfy the instruction's requirements — especially relevant across multi-round interactions where variable requirements may change between rounds.

3. **JSON Bracket Integrity**: The `<workflow>` tag contains a single-line, valid JSON string parseable by `json.loads()` in Python directly. Bracket closure is critical — truncation, mismatched brackets, and unclosed structures all invalidate the JSON. Nodes with deeply nested bracket structures (for example `if-else` cases with multiple conditions) are the most common source of bracket mismatches; verifying that every `[`, `{`, and `(` has a matching closing counterpart before finalizing avoids these errors.

4. **Escape Sequences in String Values**: JSON string values cannot contain raw control characters (newline, tab, etc.), so escaping is required. This is especially relevant for the `code` field (Python code), LLM-node message fields (the `system` and `user` keys under a `model` node's `param`), and `template` fields:
  - **Newlines** inside string values: `\n` (backslash + n), not a real line break.
  - **Tabs** inside string values: `\t` (backslash + t).
  - **Carriage returns** inside string values: `\r` (backslash + r).
  - **Double quotes** inside string values: `\"` (backslash + quote).
  - **Backslashes** that should appear literally in the final string (for example in regex patterns such as `\d{4}`, or in Jinja2 `replace('\n', ' ')`): `\\` (double backslash).
    - For example, a Jinja2 template needing `replace('\n', ' ')` is written in JSON as `replace('\\n',' ')`, because `\\n` in JSON represents the literal two-character sequence backslash+n.
  - **Common mistake**: Double-escaped forms such as `\\\\n` or `\\\\t` produce literal backslash characters in the parsed output, not actual newlines/tabs. Exactly ONE level of JSON escaping is correct, regardless of whether the string content happens to be Python code or a template — JSON only ever needs one level of escaping.
    - For example: a Python snippet containing `line.split("\t")` is written in JSON as `line.split(\"\\t\")` — `\"` escapes the double quotes, `\\t` represents a literal tab character in the parsed string.

All newlines, tabs, and carriage returns within JSON string values are represented as two-character escape sequences (`\n`, `\t`, `\r`), not as literal whitespace characters. This is especially relevant for the `code` field (Python code), LLM-node message fields (the `system` and `user` keys under a `model` node's `param`), and `template` fields.

5. **Topological Ordering of nodes_info**: The `nodes_info` array is in topological order. Nodes use "forward references" — a node only references variables from nodes that appear before it in the array. The one exception is the `output_selector` of an `iteration` node, which may reference a child node that is defined later (since iteration child nodes are created as part of the iteration).

6. **Iteration Canvas Boundary**: Edges and variable references never cross the iteration boundary. Specifically:
  - No edges exist between iteration child nodes and external nodes. External nodes connect to/from the `iteration` node itself, which acts as the sole bridge between internal and external.
  - External node variables are not referenced from inside the iteration canvas, and iteration child node variables are not referenced from outside (the iteration node's `output` is used instead).
  - Child nodes inside the iteration canvas reference the iteration node's built-in `item` and `index` variables directly (via the iteration node's id, not the `iteration-start` node's id in Dify).
  - The iteration node receives internal results via its `output_selector` parameter, which points to a child node's output variable.
  - Child nodes within an iteration canvas are connected to each other via internal edges — they are not isolated nodes.
  - On Dify, no edge exists between the `iteration` and `iteration-start` nodes.

7. **No Isolated Nodes**: Every node in the workflow is connected to at least one other node via edges. A node created without any connecting edge is invalid. The workflow is a connected DAG — all nodes (except for the child nodes within the iteration canvas) are reachable from the `start` node through the edge graph.

8. **Instruction Fidelity — No Key Node Omissions**: Producing a working workflow requires identifying every node implied or explicitly mentioned by the creation/modification instruction. A missing key node — omitting a Document Extractor when the instruction involves file content processing, or omitting an If-Else when the instruction describes conditional logic — causes the workflow to fail. A valid workflow can actually execute and solve the problem end-to-end.

9. **File-Aware Workflow Design**: Whether the instruction's input or output involves files matters for node selection:
  - Inputs mentioning `document` or `image` are typically file-typed variables.
  - Inputs with multiple optional forms (where some may be empty while others have values) are handled with an `if-else` node that detects which inputs are provided and routes to the appropriate processing branch.

10. **Format Compliance**: Creation, addition, deletion, modification, and correction all follow the structure described in *Output Format* so the response can be correctly parsed.


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

The complete list of node types, their parameter schemas, and their referable variables for each platform lives in a dedicated, pluggable documentation file under `node_docs/`:

- **Dify** → see [`node_docs/dify.md`](./node_docs/dify.md)
- **Coze** → see [`node_docs/coze.md`](./node_docs/coze.md)

Once the target platform has been resolved (see `Platform Resolution` above), the corresponding file in `node_docs/` is the authoritative reference for node `type` strings and their `param` structures. Because the two platforms have different and evolving node sets, the `node_docs/` file for the selected platform is consulted each time rather than relied on from memory.

### Note on placeholder auth fields in node schemas

Node templates for the `http-request` node (and similar) contain placeholder fields such as `bearerTokenData` with a literal `"EMPTY"` value. These are **schema placeholders** that describe what a user-authored workflow can contain; the skill does not read, request, or transmit any credentials. Users authoring a workflow should avoid pasting real API keys, bearer tokens, or passwords into the generated JSON — those values, if pasted in, would be stored verbatim in whatever artifact the user produces.
