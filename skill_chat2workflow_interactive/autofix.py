"""
autofix.py — robust post-processing for LLM-generated <workflow> responses.

This module provides auto-fix and validation utilities for the structured
response produced by the Chat2Workflow skill (three tagged sections:
<node_selection>, <design_principle>, <workflow>).

Public API (re-exported without the leading underscore for ergonomics):

    apply_all_autofixes(response_text)
        -> cleaned response text with all fixes applied

    validate_workflow(response_text)
        -> list of issue strings (empty list means all checks passed)

    extract_workflow_json(response_text)
        -> the raw JSON string between <workflow> and </workflow>

    check_workflow_json_valid(response_text)
        -> bool, whether the <workflow> JSON parses to a dict

    extract_variables_summary(workflow_json_str)
        -> human-readable summary of start-node inputs / end-node outputs

The auto-fix pipeline, in order:
    1. Strip markdown code fences wrapping the JSON inside <workflow>.
    2. Repair JSON with the `json_repair` library.
    3. Reorder `nodes_info` into topological order.
    4. Rewrite `<node_selection>` to match the node types actually used in
       `<workflow>`.
"""

import json
import re
from collections import defaultdict

from json_repair import repair_json


# -----------------------------------------------------------------------------
# 1. Code-fence stripping
# -----------------------------------------------------------------------------

def strip_workflow_code_fences(response_text):
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

    leading = re.match(r'^(?:```(?:json|JSON)?|(?:json|JSON)```)\s*\n?', stripped)
    if leading:
        stripped = stripped[leading.end():]
        changed = True

    if stripped.rstrip().endswith('```'):
        stripped = stripped.rstrip()
        stripped = stripped[:-3].rstrip()
        changed = True

    if changed:
        new_inner = '\n' + stripped + '\n'
        cleaned = response_text[:wf_match.start(2)] + new_inner + response_text[wf_match.end(2):]
        return cleaned, True

    return response_text, False


# -----------------------------------------------------------------------------
# 2. JSON repair
# -----------------------------------------------------------------------------

def fix_workflow_json(response_text):
    """
    Extract the workflow JSON from <workflow> tags, attempt JSON repair using
    the `json_repair` library (handles control chars, bracket mismatch,
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

    repaired = repair_json(inner, return_objects=False)

    # Verify the repair actually produced a dict
    try:
        parsed = json.loads(repaired)
        if not isinstance(parsed, dict):
            return response_text, False
    except json.JSONDecodeError:
        return response_text, False

    new_inner = '\n' + repaired + '\n'
    return response_text[:wf_match.start(2)] + new_inner + response_text[wf_match.end(2):], True


# -----------------------------------------------------------------------------
# 3. Topological re-ordering
# -----------------------------------------------------------------------------

def _topological_sort_nodes(nodes, edges):
    """
    Reorder nodes_info into topological order based on edges and variable
    references within node params.

    The converter processes nodes sequentially — a node can only reference
    variables from nodes that appeared earlier in the list. This function
    ensures that ordering.

    Returns:
        (sorted_nodes, was_reordered)
    """
    if not nodes:
        return nodes, False

    node_map = {n.get("id"): n for n in nodes}
    node_ids = [n.get("id") for n in nodes]

    deps = defaultdict(set)
    for edge in edges:
        if isinstance(edge, list) and len(edge) >= 3:
            src, _, tgt = edge[0], edge[1], edge[2]
            if src in node_map and tgt in node_map:
                deps[tgt].add(src)

    iteration_ids = set()
    for n in nodes:
        if n.get("type") == "iteration":
            iteration_ids.add(n.get("id"))

    def _extract_ref_ids(obj, skip_keys=None):
        refs = set()
        if isinstance(obj, list):
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
            for m in re.finditer(r"\{\{#'?([^'.#}]+)'?\..*?#\}\}", obj):
                ref_id = m.group(1)
                if ref_id in node_map:
                    refs.add(ref_id)
        return refs

    for node in nodes:
        nid = node.get("id")
        ntype = node.get("type", "")
        param = node.get("param", {})
        skip_keys = {"output_selector"} if ntype == "iteration" else None
        ref_ids = _extract_ref_ids(param, skip_keys=skip_keys)
        ref_ids.discard(nid)
        if '-' in str(nid):
            parent_id = str(nid).split('-')[0]
            if parent_id in node_map:
                deps[nid].add(parent_id)
        if nid in iteration_ids:
            ref_ids = {r for r in ref_ids if not str(r).startswith(f"{nid}-")}
        deps[nid].update(ref_ids)

    # Kahn's algorithm
    in_degree = defaultdict(int)
    adj = defaultdict(set)
    all_ids = set(node_ids)

    for nid in all_ids:
        for dep in deps[nid]:
            if dep in all_ids:
                adj[dep].add(nid)
                in_degree[nid] += 1

    queue = [nid for nid in node_ids if in_degree[nid] == 0]
    queue.sort(key=lambda x: (0 if node_map.get(x, {}).get('type') == 'start' else 1, x))

    sorted_ids = []
    original_pos = {nid: idx for idx, nid in enumerate(node_ids)}
    while queue:
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

    # Cycle detected — fall back
    if len(sorted_ids) != len(node_ids):
        return nodes, False

    sorted_nodes = [node_map[nid] for nid in sorted_ids]
    was_reordered = (sorted_ids != node_ids)
    return sorted_nodes, was_reordered


def fix_topological_order(response_text):
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


# -----------------------------------------------------------------------------
# 4. Node-selection consistency
# -----------------------------------------------------------------------------

def fix_node_selection_consistency(response_text):
    """
    Auto-fix: ensure <node_selection> exactly matches the node types in
    <workflow>. If the workflow JSON is valid, extract all unique 'type' values
    from nodes_info and rewrite the <node_selection> section to match exactly.

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
        declared_raw = ns_match.group(1).strip()
        declared_types = sorted(set(t.strip().lower() for t in re.split(r'[,;\s]+', declared_raw) if t.strip()))
        actual_lower = sorted(t.lower() for t in actual_types)
        if declared_types == actual_lower:
            return response_text, False
        fixed = response_text[:ns_match.start(1)] + new_ns_content + response_text[ns_match.end(1):]
        return fixed, True
    else:
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


# -----------------------------------------------------------------------------
# 5. Extraction / validity helpers
# -----------------------------------------------------------------------------

def extract_workflow_json(response_text):
    """
    Extract the workflow JSON string from a response that contains <workflow>
    tags. Returns the raw string between <workflow> and </workflow> (stripped),
    or None if the tags are absent.
    """
    match = re.search(r'<workflow>(.*?)</workflow>', response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def check_workflow_json_valid(response_text):
    """
    Check whether the <workflow> JSON in the response is valid and is a dict.
    """
    wf_json_str = extract_workflow_json(response_text)
    if not wf_json_str:
        return False
    try:
        parsed = json.loads(wf_json_str)
        return isinstance(parsed, dict)
    except json.JSONDecodeError:
        return False


def extract_variables_summary(workflow_json_str):
    """
    Parse the workflow JSON and extract a human-readable summary of input
    variables (from start node) and output variables (from end node(s)).
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


# -----------------------------------------------------------------------------
# 6. Comprehensive validation
# -----------------------------------------------------------------------------

def validate_workflow(response_text):
    """
    Perform comprehensive validation on the agent's response.

    Returns:
        A list of issue strings. An empty list means all checks passed.
    """
    issues = []

    dp_match = re.search(r'<design_principle>(.*?)</design_principle>', response_text, re.DOTALL | re.IGNORECASE)
    if not dp_match or not dp_match.group(1).strip():
        issues.append("MISSING_DESIGN_PRINCIPLE: No <design_principle> section found.")

    workflow_json = extract_workflow_json(response_text)
    if not workflow_json:
        issues.append("MISSING_JSON: No valid JSON object found between <workflow> tags.")
        return issues

    try:
        wf = json.loads(workflow_json)
    except json.JSONDecodeError as e:
        issues.append(f"INVALID_JSON: The workflow JSON is malformed — {e}")
        return issues

    if not isinstance(wf, dict):
        issues.append(f"INVALID_JSON_TYPE: The workflow JSON is a {type(wf).__name__}, expected a dict/object.")
        return issues

    nodes = wf.get("nodes_info", [])
    edges = wf.get("edges", [])
    if not nodes:
        issues.append("MISSING_NODES: 'nodes_info' is empty or missing.")
    if not isinstance(edges, list):
        issues.append("MISSING_EDGES: 'edges' is missing or not an array.")

    node_types = [n.get("type", "") for n in nodes]
    # Normalize ids to strings up-front: LLMs occasionally emit numeric ids
    # (e.g. 5) in nodes_info while edges use "5" as a string, or vice versa.
    # Comparing a set of mixed types would spuriously fail, so we canonicalize.
    node_ids = [str(n.get("id", "")) for n in nodes]
    if "start" not in node_types:
        issues.append("MISSING_START: No 'start' node found in nodes_info.")
    else:
        start_nodes = [n for n in nodes if n.get("type") == "start"]
        if len(start_nodes) != 1:
            issues.append(f"MULTIPLE_START: Found {len(start_nodes)} start nodes, but exactly 1 is required.")
        elif str(start_nodes[0].get("id")) != "1":
            issues.append(f"START_ID_WRONG: Start node has id '{start_nodes[0].get('id')}', but must be '1'.")
    if "end" not in node_types:
        issues.append("MISSING_END: No 'end' node found in nodes_info.")

    seen_ids = set()
    dup_ids = set()
    for nid in node_ids:
        if nid in seen_ids:
            dup_ids.add(nid)
        seen_ids.add(nid)
    if dup_ids:
        issues.append(f"DUPLICATE_IDS: Duplicate node IDs found: {sorted(dup_ids)}")

    node_id_set = set(node_ids)
    bad_edges = []
    for edge in edges:
        if isinstance(edge, list) and len(edge) >= 3:
            # Stringify edge endpoints as well, to match node_id_set above.
            src, tgt = str(edge[0]), str(edge[2])
            if src not in node_id_set:
                bad_edges.append(f"source '{src}'")
            if tgt not in node_id_set:
                bad_edges.append(f"target '{tgt}'")
    if bad_edges:
        issues.append(f"INVALID_EDGES: Edges reference non-existent node IDs: {', '.join(bad_edges)}")

    actual_types = set(t.lower() for t in node_types if t)
    ns_match = re.search(r'<node_selection>(.*?)</node_selection>', response_text, re.DOTALL | re.IGNORECASE)
    if ns_match:
        declared_raw = ns_match.group(1).strip()
        declared_types = set(t.strip().lower() for t in re.split(r'[,;\s]+', declared_raw) if t.strip())
        missing_ns = actual_types - declared_types
        extra_ns = declared_types - actual_types
        if missing_ns:
            issues.append(f"NODE_SELECTION_MISMATCH: <node_selection> is missing these types: {sorted(missing_ns)}")
        if extra_ns:
            issues.append(f"NODE_SELECTION_EXTRA: <node_selection> declares non-existent types: {sorted(extra_ns)}")
    else:
        issues.append("NODE_SELECTION_MISSING: No <node_selection> tag found.")

    iteration_nodes = {str(n.get("id")): n for n in nodes if n.get("type") == "iteration"}
    for iter_id, iter_node in iteration_nodes.items():
        # Dify iterations have a first child named "<iter_id>-1" of type iteration-start.
        # Coze iterations do NOT. We detect the convention by looking at whether
        # any node with type 'iteration-start' exists in the workflow.
        expects_iter_start = any(n.get("type") == "iteration-start" for n in nodes)
        if expects_iter_start:
            expected_start_id = f"{iter_id}-1"
            if expected_start_id not in node_id_set:
                issues.append(f"ITERATION_NO_START: Iteration node '{iter_id}' is missing its iteration-start child '{expected_start_id}'.")
        out_sel = iter_node.get("param", {}).get("output_selector", [])
        if isinstance(out_sel, list) and len(out_sel) >= 2:
            ref_id = str(out_sel[1])
            if ref_id not in node_id_set:
                issues.append(f"ITERATION_BAD_OUTPUT: Iteration node '{iter_id}' output_selector references non-existent node '{ref_id}'.")
            elif not ref_id.startswith(f"{iter_id}-"):
                issues.append(f"ITERATION_BAD_OUTPUT: Iteration node '{iter_id}' output_selector should reference an internal node ('{iter_id}-N'), but references '{ref_id}'.")

    end_nodes = [n for n in nodes if n.get("type") == "end"]
    for en in end_nodes:
        outputs = en.get("param", {}).get("outputs", [])
        if not outputs:
            issues.append(f"EMPTY_END_OUTPUTS: End node '{en.get('id', '?')}' has no output variables defined.")

    iter_id_set = set(str(n.get("id")) for n in nodes if n.get("type") == "iteration")
    seen_so_far = set()
    topo_violations = []
    for node in nodes:
        nid = str(node.get("id", ""))
        ntype = node.get("type", "")
        param = node.get("param", {})

        def _collect_refs(obj, refs, _skip_keys=None):
            if isinstance(obj, list):
                if (len(obj) == 2 and isinstance(obj[0], str)
                        and isinstance(obj[1], (str, int))
                        and str(obj[1]) in node_id_set and str(obj[1]) != nid):
                    refs.add(str(obj[1]))
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
        skip_keys = {"output_selector"} if ntype == "iteration" else None
        _collect_refs(param, refs, _skip_keys=skip_keys)
        if '-' in str(nid):
            parent_id = str(nid).split('-')[0]
            if parent_id in node_id_set:
                refs.add(parent_id)
        if nid in iter_id_set:
            refs = {r for r in refs if not str(r).startswith(f"{nid}-")}
        forward_refs = refs - seen_so_far
        if forward_refs:
            topo_violations.append(f"node '{nid}' references {sorted(forward_refs)} which appear later")
        seen_so_far.add(nid)
    if topo_violations:
        issues.append(f"TOPOLOGICAL_ORDER: nodes_info is not in topological order — {'; '.join(topo_violations[:3])}{'...' if len(topo_violations) > 3 else ''}")

    return issues


# -----------------------------------------------------------------------------
# 7. Unified auto-fix pipeline
# -----------------------------------------------------------------------------

def apply_all_autofixes(answer, verbose=False):
    """
    Apply all auto-fix operations in sequence:
      1. Strip code fences from <workflow>
      2. Repair JSON brackets and control characters
      3. Reorder nodes into topological order
      4. Fix node_selection consistency

    Args:
        answer: The LLM response text (containing the three tagged sections).
        verbose: If True, print a short note for each applied fix.

    Returns:
        The fixed answer text.
    """
    def _log(msg):
        if verbose:
            print(f"    [AutoFix] {msg}")

    answer, was_stripped = strip_workflow_code_fences(answer)
    if was_stripped:
        _log("Stripped markdown code fences from <workflow> block.")

    answer, brackets_fixed = fix_workflow_json(answer)
    if brackets_fixed:
        _log("Repaired JSON issues in <workflow> block.")

    answer, topo_fixed = fix_topological_order(answer)
    if topo_fixed:
        _log("Reordered nodes_info into topological order.")

    answer, ns_fixed = fix_node_selection_consistency(answer)
    if ns_fixed:
        _log("Fixed node_selection consistency.")

    return answer


__all__ = [
    "apply_all_autofixes",
    "validate_workflow",
    "extract_workflow_json",
    "check_workflow_json_valid",
    "extract_variables_summary",
    "strip_workflow_code_fences",
    "fix_workflow_json",
    "fix_topological_order",
    "fix_node_selection_consistency",
]


# -----------------------------------------------------------------------------
# CLI for quick testing
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Apply autofixes to an LLM <workflow> response.")
    parser.add_argument("--input", type=str, help="Path to a file containing the raw LLM response. Reads stdin if omitted.")
    parser.add_argument("--output", type=str, help="Path to write the fixed response. Writes to stdout if omitted.")
    parser.add_argument("--verbose", action="store_true", help="Print which fixes were applied.")
    parser.add_argument("--validate", action="store_true", help="Print validation issues after fixing.")
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    fixed = apply_all_autofixes(raw, verbose=args.verbose)

    if args.validate:
        issues = validate_workflow(fixed)
        if issues:
            print("Validation issues:", file=sys.stderr)
            for iss in issues:
                print(f"  - {iss}", file=sys.stderr)
        else:
            print("Validation: all checks passed.", file=sys.stderr)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(fixed)
    else:
        sys.stdout.write(fixed)
