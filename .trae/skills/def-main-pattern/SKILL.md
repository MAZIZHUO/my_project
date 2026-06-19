---
name: def-main-pattern
description: "Enforces function encapsulation (def) and main() entry point pattern in all Python scripts. Invoke when writing any .py file or Python code block."
---

# Def-Main Pattern

All Python code must be organized into well-named functions using `def`, with a single `main()` function as the orchestration entry point, guarded by `if __name__ == "__main__"`.

## CRITICAL Rules

### 1. MUST use `def main()` as the entry point

Every `.py` script must end with:

```python
if __name__ == "__main__":
    main()
```

### 2. MUST encapsulate logic in functions

No loose/top-level code except:
- `import` statements
- Constants (UPPER_CASE)
- Type aliases
- The `if __name__ == "__main__"` guard

### 3. Function naming conventions

- Use `snake_case` for function names
- Function name should describe what it does: `load_data()`, `compute_returns()`, `plot_results()`
- Keep each function focused on a single responsibility

### 4. main() is the orchestrator

`main()` should be a high-level summary of the script's workflow:

```python
def main():
    """Orchestrate the full analysis pipeline."""
    data = load_and_clean_data("input.csv")
    results = analyze(data)
    save_results(results, "output.csv")
    plot_results(results)
```

## Template

```python
"""
Module docstring: brief description of what this script does.
"""

import numpy as np
import pandas as pd

# ---- Constants ----
DATA_PATH = "data/raw.csv"
OUTPUT_PATH = "output/results.csv"


def load_data(path: str) -> pd.DataFrame:
    """Load and validate raw data."""
    ...


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and preprocess data."""
    ...


def analyze(df: pd.DataFrame) -> dict:
    """Run core analysis."""
    ...


def plot_results(results: dict) -> None:
    """Generate visualizations."""
    ...


def main():
    """Orchestrate the full pipeline."""
    raw = load_data(DATA_PATH)
    clean = clean_data(raw)
    results = analyze(clean)
    plot_results(results)


if __name__ == "__main__":
    main()
```

## For .ipynb Cells

When writing code in a Jupyter notebook cell, the same principle applies:
- Wrap the cell's logic in one or more `def` functions
- Call the function(s) at the bottom of the cell

```python
def prepare_data():
    ...

def run_analysis(df):
    ...

def main():
    df = prepare_data()
    results = run_analysis(df)
    return results

results = main()
```

## Anti-Patterns (DO NOT DO)

```python
# ❌ Loose code everywhere
data = pd.read_csv("file.csv")
data = data.dropna()
result = data.groupby("x").mean()
print(result)
plt.plot(result)
plt.show()

# ❌ Functions exist but logic still runs at top level
def analyze(df):
    ...

data = pd.read_csv("file.csv")  # ← loose
analyze(data)                    # ← loose
```

## When to Invoke

- User asks to write a Python script (.py file)
- User asks to create a new Python module
- User asks to add code to a notebook cell
- User asks to refactor existing code
- Any time Python code is being generated