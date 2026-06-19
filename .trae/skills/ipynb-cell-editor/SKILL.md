---
name: ipynb-cell-editor
description: "Safely create, append, inspect, and repair Jupyter Notebook `.ipynb` cells by editing the notebook JSON structure. Use when Codex needs to add markdown/code cells, modify notebook cells, prevent or fix accidental nested `{ \"cells\": ... }` JSON code cells, preserve outputs intentionally, or explain VS Code/Jupyter notebook refresh issues after external edits."
---

# IPYNB Cell Editor

Use this skill when editing `.ipynb` files directly. Treat notebooks as JSON documents and modify `nb["cells"]`; never append raw Python or Markdown text to the end of the file.

## Core Workflow

1. Read the notebook with `json.loads(path.read_text(encoding="utf-8"))`.
2. Inspect existing cells before editing: print index, `cell_type`, source length, and a short preview.
3. Create valid cell dictionaries:
   - Markdown: `{"cell_type": "markdown", "id": ..., "metadata": {}, "source": [...]}`
   - Code: `{"cell_type": "code", "execution_count": None, "id": ..., "metadata": {}, "outputs": [], "source": [...]}`
4. Append or insert cells only through `nb["cells"]`.
5. Write back with `json.dumps(nb, ensure_ascii=False, indent=1) + "\n"`.
6. Re-read and validate the notebook after writing.

Prefer using `scripts/append_cells.py` for append operations. It accepts a notebook path plus markdown and/or code files, then validates that the new cell sources do not start with nested notebook JSON.

## Safety Rules

- Do not put an entire notebook JSON object into a code cell.
- Do not edit `.ipynb` with plain text concatenation.
- Use `execution_count: None` and `outputs: []` for new code cells unless the user explicitly wants saved outputs.
- Preserve existing cells and outputs unless the user asks to clear or rewrite them.
- If VS Code has the notebook open, warn the user that the editor may show an old in-memory version. They may need to click Update, or close without saving and reopen.
- After repair, check file size and cell previews; a sudden huge file often means JSON was nested into a cell.

## Temporary File Rule

When creating temporary scripts (e.g., `_append_cell.py`, `_fix_cell.py`, `_inspect_nb.py`) to manipulate a target `.ipynb` file:

1. **MUST place them in the SAME directory as the target `.ipynb` file**, NOT in the project root.
2. Example: if editing `09_pyda-2e_study/08_data_wrangling_join_combine_and_reshape.ipynb`, create `_append_cell.py` in `09_pyda-2e_study/`.
3. MUST delete all temporary files immediately after use.
4. If the target directory does not exist, create it first.

## Repair Pattern

When a notebook shows a huge code cell beginning with `{ "cells": [`:

1. Parse the outer notebook JSON.
2. Locate code cells whose joined source starts with `{` and contains `"cells":`.
3. If the intended source can be recovered safely, replace that cell with the intended code cell.
4. Otherwise remove the malformed cell only after confirming it is not user-authored content.
5. Validate that all remaining cells have reasonable source previews and that no cell source starts with notebook JSON.

## Validation Snippet

Use this check after edits:

```python
import json
from pathlib import Path

p = Path("notebook.ipynb")
nb = json.loads(p.read_text(encoding="utf-8"))

print("cells:", len(nb["cells"]))
for i, cell in enumerate(nb["cells"][-5:]):
    source = "".join(cell.get("source", []))
    print(i, cell.get("cell_type"), len(source), repr(source[:120]))
    print("starts_with_json?", source.lstrip().startswith("{") and '"cells"' in source[:500])
```

## Script

Use `scripts/append_cells.py` when possible:

```bash
python scripts/append_cells.py path/to/notebook.ipynb --markdown section.md --code analysis.py
```

For temporary content, create short markdown/code files in the workspace, run the script, then remove temporary files if they are not part of the requested output.