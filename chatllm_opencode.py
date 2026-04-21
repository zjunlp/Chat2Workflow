import json
import yaml
import os
import argparse
import subprocess
import re
import shutil
import tempfile
from collections import defaultdict
from json_repair import repair_json


with open("config.yaml", 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

# Path to the opencode binary (supports ~ in path)
OPENCODE_BIN = os.path.expanduser(cfg.get("opencode_bin", "opencode"))

# Path to the skill directory (contains SKILL.md and node_docs/)
SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".agents", "skills", "chat2workflow")


# Key workflow tags that indicate a valid structured response
WORKFLOW_TAGS = ["</node_selection>", "</design_principle>", "</workflow>"]

# Sentinel prefix used to identify timeout responses
TIMEOUT_SENTINEL = "[TIMEOUT]"


def _strip_workflow_code_fences(response_text):
    """
    Auto-fix: strip markdown code fences that wrap the JSON immediately inside
    <workflow> tags.  Handles variants like ```json, ```, json```, etc.
    Code fences *inside* JSON string values are left untouched because we only
    operate on the leading/trailing lines of the <workflow> block.

    Returns:
        (cleaned_response_text, was_stripped)
    """
    wf_match = re.search(r'(<workflow>)(.*?)(</workflow>)', response_text, re.DOTALL)
    if not wf_match:
        return response_text, False

    inner = wf_match.group(2)
    stripped = inner.strip()
    changed = False

    # Remove leading code fence: ```json, ```JSON, json```, ``` etc.
    leading = re.match(r'^(?:```(?:json|JSON)?|(?:json|JSON)```)\s*\n?', stripped)
    if leading:
        stripped = stripped[leading.end():]
        changed = True

    # Remove trailing code fence: ```
    if stripped.rstrip().endswith('```'):
        stripped = stripped.rstrip()
        stripped = stripped[:-3].rstrip()
        changed = True

    if changed:
        new_inner = '\n' + stripped + '\n'
        cleaned = response_text[:wf_match.start(2)] + new_inner + response_text[wf_match.end(2):]
        return cleaned, True

    return response_text, False


def _fix_workflow_json(response_text):
    """
    Extract the workflow JSON from <workflow> tags, attempt JSON repair
    using the json_repair library (handles control chars, bracket mismatch,
    unclosed brackets, trailing commas, and many other LLM JSON mistakes).

    Returns:
        (fixed_response_text, was_fixed)
    """
    wf_match = re.search(r'(<workflow>)(.*?)(</workflow>)', response_text, re.DOTALL)
    if not wf_match:
        return response_text, False

    inner = wf_match.group(2).strip()

    # Fast path: already valid JSON
    try:
        json.loads(inner)
        return response_text, False
    except json.JSONDecodeError:
        pass

    # Use json_repair library for robust repair
    repaired = repair_json(inner, return_objects=False)

    # Verify the repair actually produced valid JSON and is a dict (workflow object)
    try:
        parsed = json.loads(repaired)
        if not isinstance(parsed, dict):
            # json_repair may produce a list or other non-dict type which is not
            # a valid workflow object — treat as failed repair
            return response_text, False
    except json.JSONDecodeError:
        return response_text, False

    new_inner = '\n' + repaired + '\n'
    return response_text[:wf_match.start(2)] + new_inner + response_text[wf_match.end(2):], True


def _topological_sort_nodes(nodes, edges):
    """
    Reorder nodes_info into topological order based on edges and variable
    references within node params.

    The converter framework processes nodes sequentially — a node can only
    reference variables from nodes that appeared earlier in the list. This
    function ensures that ordering.

    Returns:
        (sorted_nodes, was_reordered): The topologically sorted node list
        and whether any reordering was performed.
    """
    if not nodes:
        return nodes, False

    node_map = {n.get("id"): n for n in nodes}
    node_ids = [n.get("id") for n in nodes]

    # Build adjacency: for each node, which node IDs must come before it?
    # Source 1: edges (source must come before target)
    deps = defaultdict(set)
    for edge in edges:
        if isinstance(edge, list) and len(edge) >= 3:
            src, _, tgt = edge[0], edge[1], edge[2]
            if src in node_map and tgt in node_map:
                # Handle iteration internal edges: don't create dep from
                # iteration-start to iteration parent
                deps[tgt].add(src)

    # Build a set of iteration node IDs so we can handle the output_selector exception
    iteration_ids = set()
    for n in nodes:
        if n.get("type") == "iteration":
            iteration_ids.add(n.get("id"))

    # Source 2: variable references in param (scan for ["varname", "nodeID"] patterns)
    def _extract_ref_ids(obj, skip_keys=None):
        """Recursively extract node IDs referenced in param structures."""
        refs = set()
        if isinstance(obj, list):
            # Check if this is a variable reference: [name, nodeID]
            if (len(obj) == 2 and isinstance(obj[0], str) and isinstance(obj[1], str)
                    and obj[1] in node_map):
                refs.add(obj[1])
            else:
                for item in obj:
                    refs.update(_extract_ref_ids(item))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if skip_keys and k in skip_keys:
                    continue
                refs.update(_extract_ref_ids(v))
        elif isinstance(obj, str):
            # Check for {{#nodeID.var#}} patterns
            for m in re.finditer(r"\{\{#'?([^'.#}]+)'?\..*?#\}\}", obj):
                ref_id = m.group(1)
                if ref_id in node_map:
                    refs.add(ref_id)
        return refs

    for node in nodes:
        nid = node.get("id")
        ntype = node.get("type", "")
        param = node.get("param", {})
        # For iteration nodes, skip output_selector when extracting deps.
        # The converter framework handles output_selector via deferred
        # back-fill — the iteration node is allowed to forward-reference
        # its internal child nodes.
        skip_keys = {"output_selector"} if ntype == "iteration" else None
        ref_ids = _extract_ref_ids(param, skip_keys=skip_keys)
        # A node should not depend on itself
        ref_ids.discard(nid)
        # For iteration child nodes, they depend on the iteration parent
        if '-' in str(nid):
            parent_id = str(nid).split('-')[0]
            if parent_id in node_map:
                deps[nid].add(parent_id)
        # Remove deps on iteration children from the iteration node itself
        # (output_selector refs were already skipped above, but also clean
        # up any stray refs to child nodes)
        if nid in iteration_ids:
            ref_ids = {r for r in ref_ids if not str(r).startswith(f"{nid}-")}
        deps[nid].update(ref_ids)

    # Kahn's algorithm for topological sort
    in_degree = defaultdict(int)
    adj = defaultdict(set)
    all_ids = set(node_ids)

    for nid in all_ids:
        for dep in deps[nid]:
            if dep in all_ids:
                adj[dep].add(nid)
                in_degree[nid] += 1

    # Initialize queue with nodes that have no dependencies
    queue = [nid for nid in node_ids if in_degree[nid] == 0]
    # Sort to ensure deterministic order: 'start' node first, then by ID
    queue.sort(key=lambda x: (0 if node_map.get(x, {}).get('type') == 'start' else 1, x))

    sorted_ids = []
    while queue:
        # Prefer 'start' type first, then 'end' type last among available
        # Sort: start=0, end=2, others=1; then by original position
        original_pos = {nid: idx for idx, nid in enumerate(node_ids)}
        queue.sort(key=lambda x: (
            0 if node_map.get(x, {}).get('type') == 'start' else
            2 if node_map.get(x, {}).get('type') == 'end' else 1,
            original_pos.get(x, 999)
        ))
        nid = queue.pop(0)
        sorted_ids.append(nid)
        for neighbor in adj[nid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # If we couldn't sort all nodes (cycle detected), fall back to original order
    if len(sorted_ids) != len(node_ids):
        return nodes, False

    sorted_nodes = [node_map[nid] for nid in sorted_ids]

    # Check if order actually changed
    was_reordered = (sorted_ids != node_ids)
    return sorted_nodes, was_reordered


def _fix_topological_order(response_text):
    """
    Parse the workflow JSON, reorder nodes_info into topological order,
    and replace it back into the response text.

    Returns:
        (fixed_response_text, was_fixed)
    """
    wf_match = re.search(r'(<workflow>)(.*?)(</workflow>)', response_text, re.DOTALL)
    if not wf_match:
        return response_text, False

    inner = wf_match.group(2).strip()
    try:
        wf = json.loads(inner)
    except json.JSONDecodeError:
        return response_text, False

    nodes = wf.get("nodes_info", [])
    edges = wf.get("edges", [])
    sorted_nodes, was_reordered = _topological_sort_nodes(nodes, edges)

    if not was_reordered:
        return response_text, False

    wf["nodes_info"] = sorted_nodes
    new_json = json.dumps(wf, ensure_ascii=False)
    new_inner = '\n' + new_json + '\n'
    return response_text[:wf_match.start(2)] + new_inner + response_text[wf_match.end(2):], True

def _fix_node_selection_consistency(response_text):
    """
    Auto-fix: ensure <node_selection> exactly matches the node types in <workflow>.
    If the workflow JSON is valid, extract all unique 'type' values from nodes_info
    and rewrite the <node_selection> section to match exactly.

    Returns:
        (fixed_response_text, was_fixed)
    """
    wf_match = re.search(r'<workflow>(.*?)</workflow>', response_text, re.DOTALL)
    if not wf_match:
        return response_text, False

    try:
        wf = json.loads(wf_match.group(1).strip())
    except (json.JSONDecodeError, TypeError):
        return response_text, False

    nodes = wf.get("nodes_info", [])
    if not nodes:
        return response_text, False

    actual_types = sorted(set(n.get("type", "") for n in nodes if n.get("type")))
    if not actual_types:
        return response_text, False

    new_ns_content = "\n" + "\n".join(actual_types) + "\n"

    ns_match = re.search(r'<node_selection>(.*?)</node_selection>', response_text, re.DOTALL | re.IGNORECASE)
    if ns_match:
        # Check if already consistent
        declared_raw = ns_match.group(1).strip()
        declared_types = sorted(set(t.strip().lower() for t in re.split(r'[,;\s]+', declared_raw) if t.strip()))
        actual_lower = sorted(t.lower() for t in actual_types)
        if declared_types == actual_lower:
            return response_text, False
        # Replace existing node_selection
        fixed = response_text[:ns_match.start(1)] + new_ns_content + response_text[ns_match.end(1):]
        return fixed, True
    else:
        # No node_selection tag found — insert one before <design_principle> or <workflow>
        insert_point = None
        for tag in ['<design_principle>', '<workflow>']:
            idx = response_text.find(tag)
            if idx >= 0:
                insert_point = idx
                break
        if insert_point is None:
            insert_point = 0
        ns_block = f"<node_selection>{new_ns_content}</node_selection>\n\n"
        fixed = response_text[:insert_point] + ns_block + response_text[insert_point:]
        return fixed, True


def _check_design_principle_missing(response_text):
    """
    Check whether the <design_principle> section is missing or empty.
    Unlike other auto-fixable issues, a missing design_principle indicates
    the response is fundamentally incomplete and should be regenerated.

    Returns:
        True if <design_principle> is missing or empty, False otherwise.
    """
    dp_match = re.search(r'<design_principle>(.*?)</design_principle>', response_text, re.DOTALL | re.IGNORECASE)
    return not dp_match or not dp_match.group(1).strip()


def _extract_workflow_json(response_text):
    """
    Extract the workflow JSON string from a response that contains <workflow> tags.
    Mirrors the extraction logic in pass_stage.py's extract_and_format_data:
      workflow_str = match_workflow.group(1).strip()
      workflow_json = json.loads(workflow_str)

    Returns:
        The raw string between <workflow> and </workflow> tags (stripped), or None.
    """
    match = re.search(r'<workflow>(.*?)</workflow>', response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _validate_workflow(response_text):
    """
    Perform comprehensive validation on the agent's response.
    Checks multiple dimensions that correspond to evaluation pipeline steps.

    Returns:
        A list of issue strings. Empty list means all checks passed.
    """
    issues = []

    # --- Check 0: Required sections ---
    # pass_stage.py extract_and_format_data requires all three tags to be present.
    dp_match = re.search(r'<design_principle>(.*?)</design_principle>', response_text, re.DOTALL | re.IGNORECASE)
    if not dp_match or not dp_match.group(1).strip():
        issues.append("MISSING_DESIGN_PRINCIPLE: No <design_principle> section found. The evaluation pipeline requires all three sections: <node_selection>, <design_principle>, and <workflow>.")

    # --- Check 1: JSON validity ---
    workflow_json = _extract_workflow_json(response_text)
    if not workflow_json:
        issues.append("MISSING_JSON: No valid JSON object found between <workflow> tags.")
        return issues  # Can't do further checks without JSON

    try:
        wf = json.loads(workflow_json)
    except json.JSONDecodeError as e:
        issues.append(f"INVALID_JSON: The workflow JSON is malformed — {e}")
        return issues  # Can't do further checks without valid JSON

    if not isinstance(wf, dict):
        issues.append(f"INVALID_JSON_TYPE: The workflow JSON is a {type(wf).__name__}, expected a dict/object.")
        return issues  # Can't do further checks without a proper JSON object

    # --- Check 2: Structure completeness ---
    nodes = wf.get("nodes_info", [])
    edges = wf.get("edges", [])
    if not nodes:
        issues.append("MISSING_NODES: 'nodes_info' is empty or missing.")
    if not isinstance(edges, list):
        issues.append("MISSING_EDGES: 'edges' is missing or not an array.")

    # --- Check 3: Start and End nodes ---
    node_types = [n.get("type", "") for n in nodes]
    node_ids = [n.get("id", "") for n in nodes]
    if "start" not in node_types:
        issues.append("MISSING_START: No 'start' node found in nodes_info.")
    else:
        # SKILL.md requires exactly one start node with id "1"
        start_nodes = [n for n in nodes if n.get("type") == "start"]
        if len(start_nodes) != 1:
            issues.append(f"MULTIPLE_START: Found {len(start_nodes)} start nodes, but exactly 1 is required.")
        elif start_nodes[0].get("id") != "1":
            issues.append(f"START_ID_WRONG: Start node has id '{start_nodes[0].get('id')}', but SKILL.md requires id '1'.")
    if "end" not in node_types:
        issues.append("MISSING_END: No 'end' node found in nodes_info.")

    # --- Check 4: Node ID uniqueness ---
    seen_ids = set()
    dup_ids = set()
    for nid in node_ids:
        if nid in seen_ids:
            dup_ids.add(nid)
        seen_ids.add(nid)
    if dup_ids:
        issues.append(f"DUPLICATE_IDS: Duplicate node IDs found: {sorted(dup_ids)}")

    # --- Check 5: Edge references validity ---
    node_id_set = set(node_ids)
    bad_edges = []
    for edge in edges:
        if isinstance(edge, list) and len(edge) >= 3:
            src, _, tgt = edge[0], edge[1], edge[2]
            if src not in node_id_set:
                bad_edges.append(f"source '{src}'")
            if tgt not in node_id_set:
                bad_edges.append(f"target '{tgt}'")
    if bad_edges:
        issues.append(f"INVALID_EDGES: Edges reference non-existent node IDs: {', '.join(bad_edges)}")

    # --- Check 6: Node selection BIDIRECTIONAL consistency ---
    actual_types = set(t.lower() for t in node_types if t)
    ns_match = re.search(r'<node_selection>(.*?)</node_selection>', response_text, re.DOTALL | re.IGNORECASE)
    if ns_match:
        declared_raw = ns_match.group(1).strip()
        declared_types = set(t.strip().lower() for t in re.split(r'[,;\s]+', declared_raw) if t.strip())
        missing_ns = actual_types - declared_types
        extra_ns = declared_types - actual_types
        if missing_ns:
            issues.append(f"NODE_SELECTION_MISMATCH: <node_selection> is missing these types that appear in the workflow: {sorted(missing_ns)}")
        if extra_ns:
            issues.append(f"NODE_SELECTION_EXTRA: <node_selection> declares these types that do NOT appear in the workflow: {sorted(extra_ns)}. Remove them.")
    else:
        issues.append("NODE_SELECTION_MISSING: No <node_selection> tag found. The evaluation pipeline requires all three sections: <node_selection>, <design_principle>, and <workflow>.")

    # --- Check 7: Iteration structure ---
    iteration_nodes = {n.get("id"): n for n in nodes if n.get("type") == "iteration"}
    for iter_id, iter_node in iteration_nodes.items():
        # Check iteration-start exists
        expected_start_id = f"{iter_id}-1"
        if expected_start_id not in node_id_set:
            issues.append(f"ITERATION_NO_START: Iteration node '{iter_id}' is missing its iteration-start child '{expected_start_id}'.")
        # Check output_selector references an internal node
        out_sel = iter_node.get("param", {}).get("output_selector", [])
        if isinstance(out_sel, list) and len(out_sel) >= 2:
            ref_id = out_sel[1]
            if ref_id not in node_id_set:
                issues.append(f"ITERATION_BAD_OUTPUT: Iteration node '{iter_id}' output_selector references non-existent node '{ref_id}'.")
            elif not ref_id.startswith(f"{iter_id}-"):
                issues.append(f"ITERATION_BAD_OUTPUT: Iteration node '{iter_id}' output_selector should reference an internal node ('{iter_id}-N'), but references '{ref_id}'.")

    # --- Check 8: End node outputs not empty ---
    end_nodes = [n for n in nodes if n.get("type") == "end"]
    for en in end_nodes:
        outputs = en.get("param", {}).get("outputs", [])
        if not outputs:
            issues.append(f"EMPTY_END_OUTPUTS: End node '{en.get('id', '?')}' has no output variables defined.")

    # --- Check 9: Topological order ---
    # Verify that nodes_info is in topological order: every referenced node
    # must appear earlier in the array.
    # Exception: iteration nodes may forward-reference their child nodes
    # via output_selector — the converter handles this via deferred back-fill.
    iter_id_set = set(n.get("id") for n in nodes if n.get("type") == "iteration")
    seen_so_far = set()
    topo_violations = []
    for node in nodes:
        nid = node.get("id", "")
        ntype = node.get("type", "")
        param = node.get("param", {})
        # Extract all node ID references from param
        def _collect_refs(obj, refs, _skip_keys=None):
            if isinstance(obj, list):
                if (len(obj) == 2 and isinstance(obj[0], str) and isinstance(obj[1], str)
                        and obj[1] in node_id_set and obj[1] != nid):
                    refs.add(obj[1])
                else:
                    for item in obj:
                        _collect_refs(item, refs)
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    if _skip_keys and k in _skip_keys:
                        continue
                    _collect_refs(v, refs)
            elif isinstance(obj, str):
                for m in re.finditer(r"\{\{#'?([^'.#}]+)'?\..*?#\}\}", obj):
                    ref_id = m.group(1)
                    if ref_id in node_id_set and ref_id != nid:
                        refs.add(ref_id)
        refs = set()
        # For iteration nodes, skip output_selector (allowed forward reference)
        skip_keys = {"output_selector"} if ntype == "iteration" else None
        _collect_refs(param, refs, _skip_keys=skip_keys)
        # For iteration children, parent must come before
        if '-' in str(nid):
            parent_id = str(nid).split('-')[0]
            if parent_id in node_id_set:
                refs.add(parent_id)
        # Also exclude iteration child refs from iteration node itself
        if nid in iter_id_set:
            refs = {r for r in refs if not str(r).startswith(f"{nid}-")}
        forward_refs = refs - seen_so_far
        if forward_refs:
            topo_violations.append(f"node '{nid}' references {sorted(forward_refs)} which appear later")
        seen_so_far.add(nid)
    if topo_violations:
        issues.append(f"TOPOLOGICAL_ORDER: nodes_info is not in topological order — {'; '.join(topo_violations[:3])}{'...' if len(topo_violations) > 3 else ''}")

    return issues





def _apply_all_autofixes(answer):
    """
    Apply all auto-fix operations in sequence:
    1. Strip code fences from <workflow>
    2. Repair JSON brackets and control characters
    3. Reorder nodes into topological order
    4. Fix node_selection consistency

    Note: <design_principle> is NOT auto-fixed here. If it is missing,
    the response should be regenerated rather than filled with a placeholder.

    Returns:
        The fixed answer text.
    """
    answer, was_stripped = _strip_workflow_code_fences(answer)
    if was_stripped:
        print(f"    [AutoFix] Stripped markdown code fences from <workflow> block.")

    answer, brackets_fixed = _fix_workflow_json(answer)
    if brackets_fixed:
        print(f"    [AutoFix] Repaired JSON issues in <workflow> block.")

    answer, topo_fixed = _fix_topological_order(answer)
    if topo_fixed:
        print(f"    [AutoFix] Reordered nodes_info into topological order.")

    answer, ns_fixed = _fix_node_selection_consistency(answer)
    if ns_fixed:
        print(f"    [AutoFix] Fixed node_selection consistency.")

    return answer


def _check_workflow_json_valid(response_text):
    """
    Check whether the <workflow> JSON in the response is valid and is a dict.

    Returns:
        True if JSON is valid and is a dict, False otherwise.
        Also returns False if there are no <workflow> tags (caller should
        handle that case separately).
    """
    wf_json_str = _extract_workflow_json(response_text)
    if not wf_json_str:
        return False
    try:
        parsed = json.loads(wf_json_str)
        return isinstance(parsed, dict)
    except json.JSONDecodeError:
        return False


def _extract_variables_summary(workflow_json_str):
    """
    Parse the workflow JSON and extract a human-readable summary of
    input variables (from start node) and output variables (from end node(s)).

    Returns:
        A string summary, or None if parsing fails.
    """
    try:
        wf = json.loads(workflow_json_str)
    except (json.JSONDecodeError, TypeError):
        return None

    nodes = wf.get("nodes_info", [])
    input_vars = []
    output_vars = []

    for node in nodes:
        ntype = node.get("type", "")
        param = node.get("param", {})
        if ntype == "start":
            for var in param.get("variables", []):
                if isinstance(var, list) and len(var) >= 2:
                    input_vars.append(f"{var[0]} ({var[1]})")
        elif ntype == "end":
            for var in param.get("outputs", []):
                if isinstance(var, list) and len(var) >= 2:
                    src = var[1]
                    src_desc = f"from node {src[1]}.{src[0]}" if isinstance(src, list) and len(src) >= 2 else str(src)
                    output_vars.append(f"{var[0]} ({src_desc})")

    lines = []
    lines.append(f"Input variables: {', '.join(input_vars) if input_vars else 'none'}")
    lines.append(f"Output variables: {', '.join(output_vars) if output_vars else 'none'}")
    return '\n'.join(lines)


def _build_context_prefix(history_rounds, round_num):
    """
    Build a context prefix for Round 2+ queries (or retries) that includes ALL
    previous successful rounds' query instructions AND their complete responses,
    plus the latest variable summary to prevent context forgetting.

    Args:
        history_rounds: A list of (round_number, query_text, response_text) tuples
                        for all successfully completed rounds so far.
        round_num: The current round number (1+).

    Returns:
        A string to prepend to the query, or empty string if no history available.
    """
    if not history_rounds:
        return ""

    context_parts = []

    # Include ALL historical rounds (query + response) so the agent understands
    # the full evolution and can maintain consistency across rounds.
    history_lines = []
    for rnd, q_text, r_text in history_rounds:
        history_lines.append(
            f"[Round {rnd} Query]\n{q_text}\n\n"
            f"[Round {rnd} Response]\n{r_text}"
        )
    context_parts.append(
        f"<completed_rounds>\nBelow are all previous successful rounds (query + response) for context:\n\n"
        + "\n\n---\n\n".join(history_lines) + "\n</completed_rounds>"
    )

    # Extract the latest variable summary from the last round's response
    last_response = history_rounds[-1][2]
    workflow_json = _extract_workflow_json(last_response)
    if workflow_json:
        var_summary = _extract_variables_summary(workflow_json)
        if var_summary:
            context_parts.append(f"<latest_variables_summary>\nSummary of latest workflow inputs/outputs:\n{var_summary}\n</latest_variables_summary>")

    context_parts.append(
        "<multi-round_interaction_rules>\n"
        "Unless explicitly instructed to add, remove, or modify, variables and logic not mentioned "
        "in the instruction should remain unchanged.\n\n"
        "How to interpret output specifications across rounds:\n"
        "1. REPLACE — Phrases like 'needs to output X', 'should output X', or 'only needs to output X' "
        "(without additive language) mean output EXACTLY X; "
        "all previous outputs not listed are dropped.\n"
        "2. ADD — Additive language such as 'also output', 'additionally output', or 'in addition to "
        "what already exists' means append the new variables to the existing outputs.\n"
        "3. REMOVE — 'Remove the output Y' means drop only Y and keep everything else.\n"
        "4. NO MENTION — If outputs are not mentioned at all, keep them unchanged.\n"
        "5. BRANCH-SCOPED — When the instruction targets specific branches, only those branches are "
        "affected; unmentioned branches remain unchanged.\n"
        "6. If multiple branches produce the same output variables, aggregate them with a "
        "variable-aggregator node and use a single end node.\n"
        "7. If different branches produce different output variable sets, use separate end nodes "
        "for each branch.\n"
        "</multi-round_interaction_rules>"
    )

    return "\n\n".join(context_parts) + "\n\n"


def _parse_opencode_output(stdout, initial_session_id=None):
    """
    Parse JSON events from opencode stdout and extract step texts and session ID.

    Returns:
        (all_step_texts, found_session_id): list of step texts and the session ID.
    """
    all_step_texts = []
    current_step_text = ""
    found_session_id = initial_session_id

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type", "")

        if event_type in ("session.created", "session.updated"):
            sid = event.get("properties", {}).get("session", {}).get("id")
            if sid:
                found_session_id = sid

        if event_type == "step_start":
            current_step_text = ""

        if event_type == "text":
            text_content = event.get("content", "") or event.get("part", {}).get("text", "")
            current_step_text += text_content

        if event_type == "step_finish":
            if current_step_text.strip():
                all_step_texts.append(current_step_text)

    return all_step_texts, found_session_id


def _select_best_response(all_step_texts, raw_stdout=""):
    """
    Select the best response from collected step texts.

    Returns:
        (response_text, has_tags): The selected response and whether it contains workflow tags.
        has_tags is True when ALL WORKFLOW_TAGS are present, OR when at least
        </workflow> is present (since other sections can be auto-fixed).
    """
    if not all_step_texts:
        return raw_stdout or "", False

    # First priority: find a step with all three required closing tags
    for step_text in reversed(all_step_texts):
        if all(tag in step_text for tag in WORKFLOW_TAGS):
            return step_text, True

    # Second priority: find a step with at least </workflow> tag
    # (node_selection and design_principle can be auto-fixed)
    for step_text in reversed(all_step_texts):
        if '</workflow>' in step_text:
            return step_text, True

    # No step contains workflow tags; return the last step as fallback
    return all_step_texts[-1], False


def run_opencode(message, model, session_id=None, skill_dir=None, prepend_skill_instruction=True):
    """
    Run opencode with a message and return the assistant's response text and session ID.

    Args:
        message: The user query to send.
        model: The model identifier in 'provider/model' format.
        session_id: If provided, continue from this session (multi-round).
        skill_dir: The working directory for opencode. Defaults to SKILL_DIR.
        prepend_skill_instruction: Whether to prepend the SKILL.md instruction to the message.
            Set to False for follow-up messages like "continue".

    Returns:
        (response_text, session_id, has_workflow_tags): The response, session ID, and
        whether the response contains key workflow tags.
    """
    working_dir = skill_dir or SKILL_DIR
    cmd = [
        OPENCODE_BIN, "run",
        "--format", "json",
        "-m", model,
        "--dir", working_dir,
    ]

    if session_id:
        cmd.extend(["-s", session_id])

    # Prepend the skill instruction to the message and append as positional argument.
    # We read and inline the full SKILL.md content so the agent has all node
    # documentation in a single prompt without needing to call the read tool.
    if prepend_skill_instruction:
        skill_md_path = os.path.join(working_dir, "SKILL.md")
        try:
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                skill_content = f.read()
        except FileNotFoundError:
            skill_content = ""
        if skill_content:
            full_message = (
                f"Below is your complete skill instruction. Follow it precisely.\n\n"
                f"--- SKILL.md START ---\n{skill_content}\n--- SKILL.md END ---\n\n"
                f"{message}"
            )
        else:
            full_message = f"Follow the instructions in SKILL.md located in the current directory.\n\n{message}"
    else:
        full_message = message
    cmd.append(full_message)

    env = os.environ.copy()
    env["PAGER"] = "cat"

    # Use temporary files instead of capture_output=True to avoid pipe buffer
    # deadlock. When the model produces large output (long thinking content,
    # multi-round tool_calls, etc.), the 64KB OS pipe buffer fills up, blocking
    # the child process's writes while subprocess.run waits for it to exit —
    # causing a deadlock that triggers the 300s timeout. Temporary files have
    # no size limit and never block the writer.
    stdout_tmp = tempfile.NamedTemporaryFile(mode='w+', suffix='.stdout', delete=False)
    stderr_tmp = tempfile.NamedTemporaryFile(mode='w+', suffix='.stderr', delete=False)
    try:
        try:
            result = subprocess.run(
                cmd,
                stdout=stdout_tmp,
                stderr=stderr_tmp,
                text=True,
                timeout=300,  # 5 minutes timeout per query
                env=env,
            )
        except subprocess.TimeoutExpired:
            timeout_msg = f"{TIMEOUT_SENTINEL} opencode run timed out after 300 seconds"
            print(f"    {timeout_msg}")
            return timeout_msg, session_id, False

        # Read captured output from temp files
        stdout_tmp.seek(0)
        stderr_tmp.seek(0)
        stdout = stdout_tmp.read().strip()
        stderr = stderr_tmp.read().strip()
    finally:
        # Clean up temp files
        stdout_tmp.close()
        stderr_tmp.close()
        os.unlink(stdout_tmp.name)
        os.unlink(stderr_tmp.name)

    if result.returncode != 0:
        raise RuntimeError(
            f"opencode run failed (exit code {result.returncode}).\n"
            f"stderr: {stderr}\nstdout: {stdout}"
        )

    # Parse JSON events and select the best response
    all_step_texts, found_session_id = _parse_opencode_output(stdout, session_id)
    response_text, has_tags = _select_best_response(all_step_texts, raw_stdout=stdout)

    # Fallback: if no structured response found, use raw stdout
    if not response_text:
        response_text = stdout

    return response_text, found_session_id, has_tags


def process_tasks(input_path, output_path, model):
    """
    Process all tasks from input_path using opencode framework with skill,
    saving results incrementally to output_path.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        tasks_data = json.load(f)

    processed_results = []

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            processed_results = json.load(f)

    task_map = {item["task"]: item for item in processed_results}

    for item in tasks_data:
        task_name = item.get("task")
        item_id = item.get("id")
        item_category = item.get("category")

        if task_name in task_map:
            task_result = task_map[task_name]
        else:
            task_result = {"id": item_id, "category": item_category, "task": task_name}
            processed_results.append(task_result)
            task_map[task_name] = task_result

        query_keys = sorted(
            [k for k in item.keys() if k.startswith("query") and item[k]],
            key=lambda x: int(x.replace("query", ""))
        )

        try:
            # Check which queries still need processing
            pending_queries = []
            for i, q_key in enumerate(query_keys, 1):
                answer_key = f"answer{i}"
                if answer_key in task_result and task_result[answer_key]:
                    continue
                pending_queries.append((i, q_key))

            if not pending_queries:
                print(f">> Task {task_name} already completed, skipping all queries.")
                continue

            # Create a temporary copy of the skill directory to isolate each task.
            # This prevents the agent from modifying SKILL.md or polluting the
            # environment with generated files that could affect subsequent tasks.
            tmp_dir = tempfile.mkdtemp(prefix="skill_sandbox_")
            skill_copy = os.path.join(tmp_dir, "skill")
            shutil.copytree(SKILL_DIR, skill_copy)
            # Make SKILL.md read-only in the copy as an extra safeguard
            skill_md_path = os.path.join(skill_copy, "SKILL.md")
            if os.path.exists(skill_md_path):
                os.chmod(skill_md_path, 0o444)

            print(f">> Task {task_name} is currently being processed.")
            print(f"   [Sandbox] Using temporary skill dir: {skill_copy}")

            # Track ALL successful rounds' (query, response) pairs for context injection
            history_rounds = []  # list of (round_number, query_text, response_text)

            for i, q_key in enumerate(query_keys, 1):
                current_query = item[q_key]
                answer_key = f"answer{i}"

                if answer_key in task_result and task_result[answer_key]:
                    print(f"  - Query {i} already exists, skipping...")
                    # If skipping, record the stored answer and query as history context
                    history_rounds.append((i, current_query, task_result[answer_key]))
                    continue

                print(f"  - Processing Query {i}...")
                print(f"\n[current_query]\n{current_query}\n")

                # Each query starts a fresh session. Retries within the retry
                # loop also start fresh sessions to avoid context pollution.
                round_session_id = None

                # Build context prefix from all previous successful rounds' history
                context_prefix = _build_context_prefix(history_rounds, i)
                prefixed_query = f"{context_prefix}Workflow Creation Instruction for Round {i}: {current_query}"
                resp, round_session_id, has_tags = run_opencode(
                    message=prefixed_query,
                    model=model,
                    session_id=round_session_id,
                    skill_dir=skill_copy,
                )

                # Unified retry loop: validate the response comprehensively
                # (tags, JSON validity, and semantic checks via _validate_workflow)
                # after applying auto-fixes. If any issues remain, retry in a
                # brand-new session to avoid context pollution.
                max_rounds = 5
                answer = None
                for round_num in range(1, max_rounds + 1):
                    # Round 1 uses the initial response already obtained above.
                    if round_num > 1:
                        # Start a fresh session for each retry to keep the
                        # context clean — only SKILL.md + historical correct
                        # responses + current query will be present.
                        print(f"    [Round {round_num}/{max_rounds}: Resending original query in a new session...]")
                        resp, round_session_id, has_tags = run_opencode(
                            message=prefixed_query,
                            model=model,
                            session_id=None,  # new session each retry
                            skill_dir=skill_copy,
                        )

                    # Check for timeout
                    if resp.startswith(TIMEOUT_SENTINEL):
                        print(f"    [Round {round_num}/{max_rounds}: Timeout.]")
                        continue

                    # Check for workflow tags
                    if not has_tags:
                        print(f"    [Round {round_num}/{max_rounds}: No workflow tags found, will retry...]")
                        continue

                    # Remove thinking tags and apply auto-fixes
                    candidate = resp.split('</think>')[-1]
                    candidate = _apply_all_autofixes(candidate)

                    # Check JSON validity
                    if not _check_workflow_json_valid(candidate):
                        print(f"    [Round {round_num}/{max_rounds}: Response has tags but JSON is invalid after autofix, will retry...]")
                        continue

                    # Comprehensive semantic validation after auto-fix
                    remaining_issues = _validate_workflow(candidate)
                    if remaining_issues:
                        issue_summary = "\n".join(f"  - {iss}" for iss in remaining_issues)
                        print(f"    [Round {round_num}/{max_rounds}: Validation found {len(remaining_issues)} issue(s) after autofix, will retry...]")
                        print(f"{issue_summary}")
                        # Keep this candidate as a fallback in case all retries fail
                        answer = candidate
                        continue

                    # All checks passed
                    answer = candidate
                    print(f"    [Round {round_num}/{max_rounds}: Validation passed.]")
                    break
                else:
                    # Exhausted all rounds without a clean response
                    if answer is None:
                        # No candidate ever had valid tags+JSON; use last response as-is
                        answer = resp.split('</think>')[-1]
                        answer = _apply_all_autofixes(answer)
                    print(f"    [Warning: No fully valid workflow after {max_rounds} rounds, using best available response.]")

                # Log final validation state
                final_issues = _validate_workflow(answer)
                if final_issues:
                    issue_summary = "\n".join(f"  - {iss}" for iss in final_issues)
                    print(f"    [Validation] {len(final_issues)} issue(s) remain in final answer:\n{issue_summary}")
                else:
                    print(f"    [Validation] All checks passed.")

                print(f"[llm_response]\n{answer}\n")

                # Store the response and query for context injection in subsequent rounds
                history_rounds.append((i, current_query, answer))

                task_result[answer_key] = answer

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_results, f, ensure_ascii=False, indent=4)

                print(f"  - Processing Query {i}... Done")

            # Clean up the temporary sandbox directory after task completion
            shutil.rmtree(tmp_dir, ignore_errors=True)
            print(f">> All the queries for task {task_name} have been processed.")

        except Exception as e:
            print(f"An error occurred while handling task {task_name}: {e}")
            import traceback
            traceback.print_exc()
            print("The program has saved the current progress and will continue with the next task.")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(processed_results, f, ensure_ascii=False, indent=4)
            # Clean up the temporary sandbox directory on failure too
            if 'tmp_dir' in locals() and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
            continue

    print(f"\n--- All tasks have been processed ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCode + Skill baseline batch processing script")

    parser.add_argument('--input_file', type=str, required=True, help='Input JSON file path')
    parser.add_argument('--model', type=str, required=True,
                        help='Model in provider/model format (e.g., adams-deepseek-v3.1/DeepSeek-V3.1)')

    args = parser.parse_args()

    # Derive a short model name for the output filename
    model_short = args.model.split("/")[-1].lower().replace(" ", "_")
    output_file = f"output/llm_response/response_opencode_{model_short}.json"

    print(f"Input file: {args.input_file}")
    print(f"Output file: {output_file}")
    print(f"Model: {args.model}")
    print(f"Skill dir: {SKILL_DIR}")
    print(f"OpenCode bin: {OPENCODE_BIN}")

    process_tasks(args.input_file, output_file, args.model)
