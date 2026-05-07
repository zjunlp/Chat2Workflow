---
name: chat2workflow
description: An expert Dify workflow builder that designs and generates Dify-importable workflows through multi-round conversation. Produces structured JSON (nodes, edges, variable references) convertible to Dify YAML, with support for incremental add/modify/remove operations on existing workflows.
---

# Dify Workflow Builder Skill

## Overview

Dify workflows are structured as a series of connected nodes, where each node represents a specific step of logic, data processing, or model inference. The Dify workflow can be equivalently represented as JSON, where each element represents the basic parameter information of edges and nodes. You are an expert in Dify, helping users to design workflows according to their requirements.

**IMPORTANT**: The user will provide instructions for creating or modifying the workflow through an interactive conversation with you. Except for special requirements, every modification should be made on the basis of what already exists. Please provide your response according to the format specified as shown in the ## Output Format.

## Execution Constraints

This skill runs inside the **opencode** agent framework as an automated task. The following rules are **non-negotiable**:

| Rule | Detail |
|------|--------|
| **No `question` tool** | The `question` tool is DISABLED. Do not call it. Make autonomous decisions; if requirements are ambiguous, choose the most reasonable interpretation and document your assumption in `<design_principle>`. |
| **No file output** | Return the workflow as inline text in your response within the tagged sections below. Do NOT create, write, or save any JSON/YAML files. |
| **No shell commands** | Do NOT use shell commands (`cat`, `head`, `tail`, `bash`, etc.). |
| **Multi-round context** | For Round 2+ queries, the message will contain the previous workflow state inside `<previous_workflow>` tags, historical instructions inside `<previous_queries>` tags, and a variable summary inside `<previous_variables>` tags. You **MUST** parse them, preserve all existing nodes/variables, and apply only the requested changes incrementally. |


## Output Format

Your response MUST contain three clearly tagged sections as **inline text** (not files):

### 1. Node Selection
Wrapped in `<node_selection></node_selection>` tags. Reply with the names of the nodes you have chosen.

### 2. Design Principle
Wrapped in `<design_principle></design_principle>` tags. Explain your reasoning and architecture decisions. **MUST** include a "Variable Checklist" subsection that verifies input and output variables match the instruction's requirements (see Critical Rule 2).

### 3. Workflow JSON
Wrapped in `<workflow></workflow>` tags. The complete workflow as a valid JSON object.

**CRITICAL**: The JSON inside `<workflow>` tags must be raw JSON — do NOT wrap it in markdown code fences. Specifically, do NOT place ` ```json ` immediately after `<workflow>` or ` ``` ` immediately before `</workflow>`. The evaluation pipeline calls `json.loads()` directly on the content between the tags. Note: code fences that appear *inside* JSON string values (e.g. in a code node's `code` field) are fine — only the outer wrapping fences are forbidden.

## JSON Structure Specification

The JSON object describes a Directed Acyclic Graph (DAG) workflow, consisting of two core fields:

### `nodes_info` (Array)
Contains detailed configuration information for all nodes. Each element is an object representing a functional node and must contain the following fields:
- `id` (String): The unique identifier of the node, which is a string that increments starting from 1 (e.g., "1","2").
    - Note: Child nodes within an Iteration node use the format `"<ParentID>-<SeqNum>"`, where `<ParentID>` is the id of the enclosing iteration node and `<SeqNum>` is a sequential number starting from 1 that increments for each child node within that iteration canvas. For example, if the iteration node's id is `"3"`, its child nodes are `"3-1"`, `"3-2"`, `"3-3"`, etc. The `iteration-start` node must always be the first child, i.e., `"<ParentID>-1"` (e.g., `"3-1"`, `"5-1"`).
- `type` (String): The type of the node. **IMPORTANT**: The `type` value MUST exactly match the `Type` specified in the node's documentation below (e.g., the Template node's type is `template-transform`, NOT `template`). Using an incorrect type string will cause the workflow to fail.
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

2. **Variable Checklist in Design Principle**: The `<design_principle>` section MUST include a "Variable Checklist" part that verifies whether the input and output variables satisfy the instruction's requirements — especially in multi-round interactions where variable requirements may change between rounds. Note: the required input and output variable names only appear within `(variable {Name})` in the instructions. Input and output variable names must match the instruction's requirements exactly — no more, no less.

3. **JSON Bracket Integrity**: The `<workflow>` tag must contain a single-line, valid JSON string that passes json.loads() in Python directly. Pay extra attention to bracket closure — avoid truncation, mismatched brackets, or unclosed structures. The JSON must be complete and parseable. **Particular caution is needed for nodes with deeply nested bracket structures (e.g., `if-else` cases with multiple conditions), where bracket mismatches are most likely to occur. Before finalizing, mentally verify that every `[`, `{`, and `(` has a matching closing counterpart.**

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
  - Child nodes inside the iteration canvas reference the iteration node's built-in `item` and `index` variables directly (using the iteration node's id, NOT the `iteration-start` node's id).
  - The iteration node receives internal results via its `output_selector` parameter, which points to a child node's output variable.
  - Child nodes within an iteration canvas MUST be connected to each other via internal edges — they are NOT isolated nodes.
  - No edge exists between the `iteration` and `iteration-start` nodes.

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
| **"Only output"** — "needs to output X" / "should output X" / "only needs to output X" (without additive language) | Output exactly X. This is a fresh specification — REPLACE all previous outputs. Previous outputs NOT listed are dropped. |
| **"Additionally add"** — Additive language (any phrasing conveying "in addition to what already exists") | ADD the new variables to existing outputs. |
| **"Remove"** — "Remove the output Y" | Remove only Y, keep all others. |
| **"No mention"** — No mention of outputs | Keep them unchanged. |
| **"Branch-scoped change"** — In a branching workflow, the output specification constrains only the branch(es) it refers to | Unmentioned branches remain unchanged. |
| **Multi-branch same outputs** | If multiple branches output the same variables, aggregate them with `variable-aggregator` and use a single `end` node. |
| **Multi-branch different outputs** | If different branches produce different output variable sets, use separate `end` nodes for each branch. |


---

## Complete Node Documentation

Here are the meta information to the nodes that may be used in the workflow:

### Node: Start
- **Type**: `start`
- **Description**: The "Start" node is a critical preset node in the workflow application. It provides essential initial information, such as user input and uploaded files, to support the normal flow of the application and subsequent workflow nodes.
- **Parameters**:
  - `variables`: `Array<[string, string]>`
    - Description: Define the set of input variables required by the node.
    - Value: Each array `[Name, Type]` strictly adheres to the following order.
        - Index 0: **Variable Identifier** (`string`), used to reference the variable within the context.
        - Index 1: **Type Specifier** (`string`), declares the data format accepted by the variable. Allowed Values: `"string"`, `"number"`, `"boolean"`, `"file"`, `"array[file]"`.
    - Example: `[["query", "string"], ["limit", "number"], ["file_A", "file"]]`
- **Referable Variables**: Each variable in `"variables"` can be referenced by downstream nodes.
- **Supplementary Information**:
  1. The uploaded file is available as a variable containing `type` sub-variable. Allowed value for `type`: `"document"`, `"image"`, `"video"`, `"audio"`. **Note: `type` sub-variable should be represented as `<File Variable Name>.type`.**
  2. File Processing: Files uploaded through a Start node must be processed appropriately by subsequent nodes. The Start node only collects files; it does not read or parse their content. Therefore, you need to connect specific nodes to extract and process the file content. For example:
      - Document files can be routed to a Doc Extractor node for text extraction so that LLMs can understand their content.
      - Images can be sent to LLM nodes with vision capabilities or specialized image processing tool nodes.
      - Structured data files such as CSV or JSON can be processed with Code nodes to parse and transform the data.
  3. Every workflow MUST have exactly one `start` node with id `"1"`.


### Node: End
- **Type**: `end`
- **Description**: Define the final output content of a workflow. Every workflow needs at least one end node after complete execution to output the final result.

  The end node is a termination point in the process; no further nodes can be added after it. In a workflow application, results are only output when the end node is reached. If there are conditional branches in the process, multiple end nodes need to be defined.

  The end node must declare one or more output variables, which can reference any upstream node's output variables.
- **Parameters**:
  - `outputs`: `Array<[string, [string, string]]>`
    - Description: Defines the set of output variables of the workflow.
    - Value: Each array `[Name, ValueRef]` strictly adheres to the following order.
        - Index 0: **Current Identifier** (`string`) — The name of the current variable defined in the node.
        - Index 1: **Value Reference** (`[string, string]`) — A tuple defining the source of the value `[Source Variable Name, Source Node ID]`.
            - **Inner Index 0**: **Source Variable Name** (`string`) — The specific variable name within the target node to retrieve.
            - **Inner Index 1**: **Source Node ID** (`string`) — The unique identifier of the upstream node where the variable originates.
    - Example: `[["ans1", ["out1", "3"]], ["ans2", ["out2", "3"]]]`
- **Notes**:
  - Output variable names (CurrentIdentifier) must match exactly what the user requirement specifies.
  - **Single end node**: When all branches produce the same output variables (possibly via `variable-aggregator`), use one `end` node.
  - **Multiple end nodes**: When different branches produce different output variable sets, use separate `end` nodes for each branch.


### Node: LLM
- **Type**: `llm`
- **Description**: The LLM node invokes language models to process text, images, and documents. It sends prompts to your configured models and captures their responses.
- **Parameters**:
  1. `system`: `string`
      - Description: System prompt used to define LLM behavior.
      - Value: Text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model.
      - Example: `"You are a technical documentation expert."`
  2. `user`: `string`
      - Description: User prompt used to provide input to the LLM.
      - Value: Text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model.
      - Example: `"Please interpret the following document: {{#'3'.out2#}}"`
- **Referable Variables**: `text` (`string`) — The response content generated by LLM.
- **Supplementary Information**:
  1. For multimodal models, file and image variables can be directly placed in the user prompt.(**Note**: They cannot be included in the system prompt!)
  2. It is allowed that the system prompt is an empty string, while only the user prompt is set.

### Node: Question Classifier
- **Type**: `question-classifier`
- **Description**: The Question Classifier node intelligently categorizes user input to route conversations down different workflow paths. Instead of building complex conditional logic, you define categories and let the LLM determine which one fits best based on semantic understanding.
- **Parameters**:
  1. `query_variable_selector`: `[string, string]`
      - Description: Select what to classify, which can be any text variable from previous workflow nodes.
      - Value: The standard reference tuple `[Source Variable Name, Source Node ID]`
      - Example: `["query","1"]`
  2. `classes`: `Array<string>`
      - Description: A list of string labels representing the target categories for classification.
      - Value: Must contain at least two distinct category names.
      - Example: `["Chinese","English","Math"]`
- **Referable Variables**: `class_name` (`string`) — The classification output label.
- **Supplementary Information**: Each label maps to an output port in sequential order. Output port numbers are 0, 1, 2... in sequence. For example, when there are 3 classes, namely 'Chinese', 'English' and 'Math' in sequence, then 'Chinese' corresponds to port 0, 'English' corresponds to port 1, and 'Math' corresponds to port 2.


### Node: Code
- **Type**: `code`
- **Description**: The Code node allows you to embed custom Python scripts into your workflow to manipulate variables in ways that built-in nodes cannot achieve. It can simplify your workflow and is suitable for scenarios such as arithmetic operations, JSON transformations, text processing, and more. 

  To use variables from other nodes in a Code node, you must select them in the variables field and then reference them in your code.
- **Parameters**:
  1. `variables`: `Array<[string, [string, string]]>`
      - Description: Define input variables to access data from other nodes in your workflow, then reference these variables in your code.
      - Value: Each array is a standard tuple `[Name, ValueRef]`, where `ValueRef` is a standard reference tuple `[Source Variable Name, Source Node ID]`.
      - Example: `[["arg1",["query","1"]],["arg2",["query2","1"]]]`
  2. `outputs`: `Array<[string, string]>`
      - Description: Define the set of output variables.
      - Value: Each array is a standard tuple `[Name, Type]`.
          - Allowed Values for `Type`: `"string"`, `"number"`, `"boolean"`, `"object"`, `"array[string]"`, `"array[number]"`, `"array[boolean]"`, `"array[object]"`.
      - Example: `[["out1","array[string]"],["out2","string"]]`
  3. `code`: `string`
      - Description: Python code function.
      - Value: Your function must receive the input variables that you've declared, and return a dictionary containing the output variables you've declared. **Note**: Format the code using `\n` for newlines and use `\t` for each indentation level.
      - Example: `"def main(arg1: str, arg2: str):\n\treturn {\n\t\t\"out1\": [arg1,arg2],\n\t\t\"out2\": arg1\n\t\t}"`
- **Referable Variables**: Each variable in `"outputs"` can be referenced by downstream nodes.


### Node: Document Extractor
- **Type**: `document-extractor`
- **Description**: The Document Extractor node converts uploaded files into text that LLMs can process. Since language models can't directly read document formats like PDF or DOCX, this node serves as the essential bridge between file uploads and AI analysis.
- **Parameters**:
  - `variable_selector`: `[string, string]`
    - Description: Select a single file input from a file variable (typically from the Start node) or multiple files as an array for batch document processing. The type of the received variable can only be `"file"` or `"array[file]"`.
    - Value: The standard reference tuple `[Source Variable Name, Source Node ID]`.
    - Example: `["file_A","1"]`
- **Referable Variables**: `text` (`string / array[string]`) — The extracted text. Single file input produces a string containing the extracted text. Multiple file input produces an `array[string]` with each file's content.


### Node: HTTP Request
- **Type**: `http-request`
- **Description**: This node allows sending server requests via the HTTP protocol, suitable for scenarios such as retrieving external data. The node only supports GET request method at present.
- **Parameters**:
  - `url`: `[string, string]`
    - Description: The URL address of the GET request to be sent.
    - Value: The standard reference tuple `[Source Variable Name, Source Node ID]`. The reference variable should be a url of type string.
    - Example: `["query","1"]`
- **Referable Variables**: `body` (`string`) — Response content.


### Node: If-Else
- **Type**: `if-else`
- **Description**: The If-Else node adds decision-making logic to your workflows by routing execution down different paths based on conditions you define. It evaluates variables and determines which branch your workflow should follow.

  1. **Branching Logic**
  The node supports multiple branching paths to handle complex decision trees: 
  IF Path executes when the primary condition evaluates to true.
  ELIF Paths provide additional conditions to check in sequence when the IF condition is false. You can add multiple ELIF branches for complex logic.
  ELSE Path serves as the fallback when no conditions match, ensuring your workflow always has a path to follow.
  **Each path is regarded as a case.**

  2. **Condition Types**
  Each case contains at least one condition. The available **Comparison Operator** depend on the variable's data type:
      - For `string` variables: contains, not contains, start with, end with, is, is not, empty, not empty.
          - **Exception: For sub-variable `type` of `file`: in, not in.**
      - For `number` variables: '≠', '=', '>', '<', '≥', '≤', empty, not empty.
      - For `boolean` variables: is, is not. (The corresponding comparison value can only be the string 'true' or 'false', not a boolean value)
      - For `object` variables: is, is not, empty, not empty.
      - For `file` variables: exists, not exists.
      - For `array[string]`/`array[number]`/`array[boolean]` variables: contains, not contains, empty, not empty.
      - For `array[object]` variables: empty, not empty.
      - For `array[file]` variables: contains, not contains, empty, not empty, all of. (The corresponding comparison value can only be 'document'/'image'/'video'/'audio')

  3. **Complex Conditions**
  Within a case, combine multiple conditions using **Logical Operator** for sophisticated decision-making:
  AND Logic requires all conditions to be true. Use this when you need multiple criteria to be met simultaneously.
  OR Logic requires any condition to be true. Use this when you want to trigger the same action for different scenarios.

  4. **Variable References**
  Reference any variable from previous workflow nodes in your conditions. Variables can come from user input, LLM responses, API calls, or any other workflow node output.
  Use the variable selector to choose from available variables, or type variable names directly using the `{{#<Source Node ID>.<Source Variable Name>#}}` syntax. Variables are replaced with actual values before reaching the model.

- **Parameters**:
  - `cases`: `Array<[string | null, Array<Condition>]>`
    - Description: An ordered list of branching cases. The workflow evaluates these sequentially.
    - Value: Each case is a **2-element array** defined as:
        - **Index 0**: **Logical Operator** (`string | null`) — It is used to combine multiple conditions, which can be `null`/'and'/'or'. When there is only one condition, return `null`.
        - **Index 1**: **Condition Group** (`Array<ConditionTuple>`) — A list of logical conditions that must be met for this branch to execute.
            - **ConditionTuple Definition**: A logical expression represented as an array `[VariableRef, ComparisonOperator, ComparisonValue?]`.
                - **Index 0**: **Variable Reference** (`[string, string]`) — The standard reference tuple: `[Source Variable Name, Source Node ID]`.
                - **Index 1**: **Comparison Operator** (`string`) — The comparison logic.
                - **Index 2**: **Comparison Value** (`string | number | boolean | object | Optional`) — The target value to compare against. *Note: This element is omitted if the **Comparison Operator** is unary ("empty"/"not empty"/"exists"/"not exists").*
    - Example: `[[null, [[["query2","1"],"=",5]]],[null,[[["query","1"],"empty"]]]]`
- **Supplementary Information**: Each case maps to an output port in sequential order. Output port numbers are 0, 1, 2... in sequence. For example, when there are 3 cases, namely IF Path, ELIF Path and ELSE Path in sequence, then IF Path corresponds to port 0, ELIF Path corresponds to port 1, and ELSE Path corresponds to port 2.


### Node: List Operator
- **Type**: `list-operator`
- **Description**: The List Operator node processes arrays by filtering, sorting, and selecting specific elements. Use it when you need to work with mixed file uploads, large datasets, or any array data that requires separation or organization before downstream processing.

  1. **The Array Processing Problem**:
  Most workflow nodes expect single values, not arrays. When you have mixed content like [image.png, document.pdf, audio.mp3] in one variable, you need to separate this into focused streams that downstream nodes can process effectively.
  The List Operator acts as an intelligent router, using filters to separate mixed arrays and prepare them for specialized processing.

  2. **Supported Data Types**: 
  The list operation node only accepts variables with the following data structures: `array[string]`, `array[number]`, `array[boolean]`, `array[object]`, `array[file]`.

  3. **List Operator**: 
  The available List Operator: extract_by, limit, order_by, filter_by.
      - a. **extract_by**: You can choose a value between 1-20, used to select the N-th item of the array variable. (The corresponding Value1 can only be number 1-20)
      - b. **limit**: You can choose a value between 1-20, used to select the first N items of the array variable. (The corresponding Value1 can only be number 1-20)
      - c. **order_by**: Ascending (asc) - Smallest to largest values, A-Z alphabetical order. Descending (desc) - Largest to smallest values, Z-A reverse order. (The corresponding Value1 can only be "asc"/"desc")
      - d. **filter_by**: Process arrays in input variables by adding filter conditions. Sort out all array variables that meet the conditions from the array, which can be understood as filtering the attributes of variables. (The corresponding Value1 can only be: {'≠','=','>','<','≥','≤',empty,not empty} for `array[string]`/`array[number]`, {is, not is} for `array[boolean]`, {in, not in} for `array[file]`. The corresponding Value2 can only be: {'true','false'} for `array[boolean]`, {document, image, video, audio} for `array[file]`)

- **Parameters**:
  1. `variable`: `[string, string]`
      - Description: Define the input variable required by the node.
      - Value: The standard reference tuple `[Source Variable Name, Source Node ID]`.
      - Example: `["query","1"]`
  2. `operator`: `[string, string | number, string | number | Optional]`
      - Description: The types of operations that can be performed on the list with corresponding values.
      - Value: `[ListOperator, Value1, Value2]` strictly adheres to the order.
          - *Note*: Value2 exists only when `**ListOperator** == 'filter_by' and 'empty' not in **Value1**`
      - Example: `["extract_by",10]`
- **Referable Variables**:
  - `result`: `array[{item_type}]` — Filtering result, data type is an array that is the same as the input variable. If the array contains only 1 file, the output variable contains only 1 array element.
  - `first_record`: `{item_type}` — The first element of the filtered array, i.e., result[0].
  - `last_record`: `{item_type}` — The last element of the filtered array, i.e., result[array.length-1].
- **Supplementary Information**: Value2 can be formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the node.


### Node: Parameter Extractor
- **Type**: `parameter-extractor`
- **Description**: The Parameter Extractor node converts unstructured text into structured data using LLM intelligence. It bridges the gap between natural language input and the structured parameters that tools, APIs, and other workflow nodes require.
- **Parameters**:
  1. `query`: `[string, string]`
      - Description: Define the input variable required by the node.
      - Value: The standard reference tuple `[Source Variable Name, Source Node ID]`.
      - Example: `["query","1"]`
  2. `parameters`: `Array<[string, string, string]>`
      - Description: Define the parameters you want to extract.
      - Value: Each array `[Description, Parameter Name, Data Type]` strictly adheres to the following order.
          - Index 0: **Description** (`string`) — Helps the LLM understand what to extract.
          - Index 1: **Parameter Name** (`string`) — The identifier of the parameter to be extracted.
          - Index 2: **Data Type** (`string`) — Allowed Values: `string`, `number`, `boolean`, `array[string]`, `array[number]`, `array[boolean]`, `array[object]`.
      - Example: `[["The number of boys in the class","num_male","number"],["The number of girls in the class","num_female","number"]]`
  3. `instruction`: `string`
      - Description: Write clear instructions describing what information to extract and how to format it. Providing examples in your instructions improves extraction accuracy and consistency for complex parameters.
      - Value: Text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model.
      - Example: `"Extract the number of students of both genders in the class from the given text{{#'3'.out2#}}"`
- **Referable Variables**: Each variable in `"parameters"` can be referenced by downstream nodes.


### Node: Template
- **Type**: `template-transform`
- **Description**: The Template node transforms and formats data from multiple sources into structured text using Jinja2 templating. Use it to combine variables, format outputs, and prepare data for downstream nodes or end users.
- **Parameters**:
  1. `variables`: `Array<[string, [string, string]]>`
      - Description: Define input variables to access data from other nodes in your workflow, then reference these variables in template.
      - Value: Each array is a standard tuple `[Name, ValueRef]`, where `ValueRef` is a standard reference tuple `[Source Variable Name, Source Node ID]`.
      - Example: `[["arg1",["query","1"]],["arg2",["query2","1"]]]`
  2. `template`: `string`
      - Description: Template nodes use Jinja2 templating syntax to create dynamic content that adapts based on workflow data.
      - Value: Text that can contain reference variables using double curly braces `{{variable_name}}`. Variables are replaced with actual values before reaching the model.
      - Example: `"The first parameter is {{arg1}}\n, and the second parameter is {{arg2}}\n\n. The above are all the parameter contents. Please analyze based on the above information."`
- **Referable Variables**: `output` (`string`) — Transformed content.
- **Notes**: Template syntax is Jinja2: `{{var}}` for output, `{% for %}...{% endfor %}` for loops, `{% if %}...{% endif %}` for conditionals. This is different from LLM prompt variable syntax (which uses `{{#NodeID.VarName#}}`).


### Node: Variable Aggregator
- **Type**: `variable-aggregator`
- **Description**: Aggregate variables from multiple branches into a single variable to achieve unified configuration for downstream nodes.

  The variable aggregation node (formerly the variable assignment node) is a key node in the workflow. It is responsible for integrating the output results from different branches, ensuring that regardless of which branch is executed, its results can be referenced and accessed through a unified variable. This is particularly useful in multi-branch scenarios, as it maps variables with the same function from different branches into a single output variable, avoiding the need for repeated definitions in downstream nodes.
- **Parameters**:
  - `variables`: `Array<[string, string]>`
    - Description: Variables from different workflow branches that you want to combine. All aggregated variables must be the same data type.
    - Value: Each array is a standard reference tuple `[Source Variable Name, Source Node ID]`.
    - Example: `[["query","1"],["query2","1"]]`
- **Referable Variables**: `output` (`{type}`) — The Variable Aggregator outputs the value from whichever branch actually executed. Since only one branch runs in conditional workflows, only one input variable will have a value during execution.


### Node: Iteration
- **Type**: `iteration`
- **Description**: The Iteration node processes arrays by running the same workflow steps on each element sequentially or in parallel. Use it for batch processing tasks that would otherwise hit limits or be inefficient as single operations.

  The node takes an array input and creates a sub-workflow that runs once for each array element. During each iteration, the current item and its index are available as variables that internal nodes can reference.

  Core Components:
  - Input Variables — Array data from upstream nodes
  - Internal Workflow — The processing steps to perform on each element
  - Output Variables — Collected results from all iterations (also an array)

- **Parameters**:
  1. `iterator_selector`: `[string, string]`
      - Description: Define the input array variable required by the node.
      - Value: The standard reference tuple `[Source Variable Name, Source Node ID]`.
      - Example: `["query","1"]`
  2. `output_selector`: `[string, string]`
      - Description: Define the output variable from internal sub-workflow.
      - Value: The standard reference tuple `[Source Variable Name, Source Node ID]`.
      - Example: `["nums","8-2"]`
- **Referable Variables**:
  - `output` (`array[{output_variable_type}]`) — Each element is the variable corresponding to `output_selector`.
  - `index` (`number`) — Built-in Variable used by nodes of internal sub-workflow. The current iteration index (starting from 0).
  - `item` (`{input_item_type}`) — Built-in Variable used by nodes of internal sub-workflow. The current array element being processed.
- **Notes**:
  - Internal node IDs follow `"<ParentID>-<N>"` pattern.
  - Reference `item` and `index` from the **iteration node itself**, NOT from `iteration-start`.
  - Internal edges connect only internal nodes; external edges connect to/from the iteration node.


### Node: Iteration-Start
- **Type**: `iteration-start`
- **Description**: This node is created immediately along with the emergence of Iteration node, which serves as the starting point of the internal workflow. This node has no variables that can be referenced.
- **Parameters**: This node contains no parameters.


### Node: Text to Speech
- **Type**: `tts`
- **Description**: This node is used for text-to-speech conversion.
- **Parameters**:
  - `text`: `string`
    - Description: The text to be converted into speech.
    - Value: Text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model.
    - Example: `"Hello everyone. The topic of my speech today is how to cultivate research capabilities. I will elaborate from the following aspects. {{#'4'.out#}}"`
- **Referable Variables**: `files` (`array[file]`) — The generated audio files.


### Node: Text to Image
- **Type**: `text2image`
- **Description**: This node is used for text-to-image generation.
- **Parameters**:
  - `prompt`: `string`
    - Description: The prompt for generating images. Describe in detail what you would like to see in the image.
    - Value: Text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model.
    - Example: `"Please generate a picture of a little bird for me."`
- **Referable Variables**: `files` (`array[file]`) — The generated image files.


### Node: Mermaid Converter
- **Type**: `mermaid-converter`
- **Description**: This node is used for converting Mermaid chart code to images.
- **Parameters**:
  - `mermaid_code`: `string`
    - Description: The Mermaid chart syntax code to be converted to an image.
    - Value: Text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model. The text must be Mermaid chart syntax code.
    - Example: `"graph TD\n    A[Start] --> B{Decision}\n    B -->|Yes| C[Process 1]\n    B -->|No| D[Process 2]\n    C --> E[End]\n    D --> E"`
- **Referable Variables**: `files` (`array[file]`) — The generated image files.


### Node: Markdown Exporter
- **Type**: `markdown-exporter`
- **Description**: This node is used to export Markdown as DOCX, PPTX, PDF, PNG, HTML, MD files.
- **Parameters**:
  1. `target_type`: `string`
      - Description: The conversion file type of the target.
      - Allowed Value: docx, pptx, pdf, png, html, md.
      - Example: `"pdf"`
  2. `md_text`: `string`
      - Description: Markdown format text.
      - Value: Markdown format text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model.
      - Example: `"{{#'2'.out3#}}"`
- **Referable Variables**: `files` (`array[file]`) — The exported files.


### Node: Google Search
- **Type**: `google-search`
- **Description**: This node is used for performing Google SERP searches and extracting fragments and web pages. The input should be a search query.
- **Parameters**:
  - `query`: `string`
    - Description: Search query.
    - Value: Text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model.
    - Example: `"Systematically study vocal music"`
- **Referable Variables**: `json` (`array[object]`) — This JSON is a nested array structure containing a root-level list with a single object. This object is bifurcated into two primary arrays: `organic_results`, which contains dictionaries with the keys `title`, `link`, and `snippet`; and `search_results`, which contains dictionaries with the keys `title`, `url`, `content`, `site_name`, and `date`.


### Node: Echarts
- **Type**: `echarts`
- **Description**: This node is used to generate visual ECharts charts. You can use it to create various types of charts such as bar charts, line charts, and pie charts.
- **Parameters**:
  1. `chart_type`: `string`
      - Description: The chart type of the target.
      - Allowed Value: line, pie, bar. **Note: This value cannot use reference variables.**
      - Example: `"pie"`
  2. `chart_title`: `string`
      - Description: The title of the chart.
      - Value: Text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model.
      - Example: `"The quantity of fruits"`
  3. `data`: `string`
      - Description: Data for generating a line chart, with numbers separated by ';'.
      - Value: Text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model.
      - Example: `"12;31;25"`
  4. `x_axisORcategories`: `string`
      - Description: For line charts and bar charts, it represents the x_axis; For pie charts, it represents the category. Each part should be separated by ';'.
      - Value: Text that can contain reference variables, formatted as `{{#<Source Node ID>.<Source Variable Name>#}}`. Variables are replaced with actual values before reaching the model.
      - Example: `"apple;banana;pear"`
- **Referable Variables**: `text` (`string`) — The generated echarts format code.
