# SAFETY_AUDIT — Chat2Workflow skill

This document is a short, reviewer-facing summary of what the bundled helper
scripts do (and do **not** do), written so a reviewer or static scanner can
confirm the skill's scope without needing to read ~1,800 lines of Python.

The scripts themselves have **not** been shortened; they are too long to show
inline in `SKILL.md`, which is why this separate audit sheet exists.

---

## 1. What actually ships

| File | Lines | Role |
|---|---|---|
| `converter.py` | ~591 | Offline CLI: reads a workflow JSON, writes a Dify YAML or Coze ZIP. |
| `tools.py` | ~641 | Pure helpers: layout math, variable lookup, node construction. Imported by `converter.py`. |
| `autofix.py` | ~630 | Offline string/JSON cleanup: strip code fences, run `json_repair`, topological reorder, reconcile `<node_selection>` with the emitted nodes. |
| `bash_converter.sh` | ~35 | Thin wrapper that invokes `python converter.py` locally with forwarded CLI args. |
| `nodes/` | many | Pure Python data classes describing Dify / Coze node schemas (type strings, parameter slots, icons). No runtime behavior beyond `__init__`. |

The three large files all operate on local files and in-memory data structures
only. They are invoked **exclusively** via `converter.py`'s CLI (`--json_path`
or `--json_str`, plus `--output_path`, `--name`, `--type`).

---

## 2. Verifiable safety properties

Every claim below can be reproduced with a single `grep` from the skill root.

### 2.1 No network I/O

```bash
grep -RInE '\b(requests|urllib|urllib2|urllib3|httplib|http\.client|socket|asyncio|aiohttp|paramiko|ftplib|smtplib|boto3|websocket|grpc)\b' \
    converter.py tools.py autofix.py bash_converter.sh
# expected: (no matches)
```

None of the four helper files imports or references any network library.

### 2.2 No shell execution / no dynamic code execution

```bash
grep -RInE '\b(subprocess|os\.system|os\.popen|os\.spawn|os\.exec[a-z]*|pty\.|eval\(|exec\()\b' \
    converter.py tools.py autofix.py
# expected: (no matches)
```

`converter.py` / `tools.py` / `autofix.py` do not shell out and do not `eval`
or `exec` strings. `bash_converter.sh` contains exactly one `python` call
(`python converter.py …`) — that is the entry point the user runs manually;
the Python files themselves never spawn a subprocess.

### 2.3 No environment-variable or credential access

```bash
grep -RInE '\b(os\.environ|os\.getenv|getenv|getpass|keyring|secrets\.|dotenv|load_dotenv|API_KEY|TOKEN|SECRET|PASSWORD)\b' \
    converter.py tools.py autofix.py bash_converter.sh
# expected: (no matches)
```

No helper reads environment variables, `.env` files, system keyrings, or any
credential store. The `token` / `bearerTokenData` strings that appear inside
`nodes/coze/basic/http_request.py` are **schema key names** in the Coze
workflow JSON format (their `value` is the placeholder string `"EMPTY"`) —
they describe what a user's authored workflow can contain, not runtime
credential access.

### 2.4 No outbound URLs in helper scripts

```bash
grep -RInE '(https?://|ftp://|ws://|wss://)' \
    converter.py tools.py autofix.py bash_converter.sh
# expected: (no matches)
```

URLs only appear in `nodes/*/` node-class files, and only as the `self.icon`
string for each node type — those are Dify / Coze UI icon constants baked
into the destination platform's schema, never fetched by this skill.

---

## 3. Exact import inventory

For full transparency, here are the complete, verbatim import lines from each
of the three large helpers (reproducible with `grep -n '^\(import\|from\) ' …`).

### `converter.py`

```
import json
import yaml
import os
import shutil
import sys
import tempfile
import zipfile
from tools import layout_nodes, construct, search_var, construct_coze
```

### `tools.py`

```
import os
import re
import ast
import yaml
import collections
from nodes.dify.basic.<...>   (local node-class modules, 17 lines)
from nodes.dify.tool.<...>    (local node-class modules, 6 lines)
from nodes.coze.basic.<...>   (local node-class modules, 13 lines)
from nodes.coze.tool.<...>    (local node-class modules, 6 lines)
```

### `autofix.py`

```
import json
import re
from collections import defaultdict
from json_repair import repair_json
```

The only third-party imports are `yaml` (PyYAML — YAML emitter) and
`json_repair` (pure-Python JSON-repair library). Both are listed in
`requirements.txt`; neither performs network activity.

---

## 4. File-system write policy (enforced in `converter.py`)

- The CLI flag `--output_path` controls where artifacts are written.
- If `--output_path` is omitted, output defaults to the sibling directory
  `../chat2workflow_output/` next to the skill folder.
- If `--output_path` resolves **inside** the skill directory, `converter.py`
  rejects it and redirects to `../chat2workflow_output/` instead, so the
  skill folder itself is never written to.
- Coze ZIP bundling uses `tempfile.mkdtemp()`; those temp files are removed
  once the final ZIP is emitted.
- `converter.py` sets `sys.dont_write_bytecode = True` before importing
  sibling modules, so running it does not create `__pycache__/` or `*.pyc`
  files next to the skill sources.

---

## 5. Invocation model

The skill itself (producing the three tagged sections `<node_selection>`,
`<design_principle>`, `<workflow>`) is **text-only**. Generating that output
does not invoke any script in this folder.

`converter.py` / `bash_converter.sh` run only when:

1. a user manually runs them from the command line, or
2. a user explicitly asks, in a given turn, that the workflow be compiled
   into a Dify YAML / Coze ZIP artifact.

In both cases the execution is local, offline, and bounded to the inputs
listed in §4 above.
