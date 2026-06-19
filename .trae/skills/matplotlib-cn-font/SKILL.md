---
name: matplotlib-cn-font
description: "Ensures matplotlib charts with Chinese text render correctly. Invoke when generating any matplotlib/seaborn plot code that contains Chinese labels, titles, legends, or annotations."
---

# Matplotlib Chinese Font

This skill ensures that any matplotlib/seaborn chart code containing Chinese characters will render correctly (no tofu/boxes) on Windows.

## CRITICAL Rule

**Whenever generating Python code that uses `matplotlib` or `seaborn` to create charts with ANY Chinese text (titles, axis labels, legends, annotations, tick labels), MUST include the following lines BEFORE any plotting calls:**

```python
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
```

## When to Invoke

- User asks to generate a chart/plot with Chinese content
- User asks to add a cell that contains `plt.plot()`, `plt.bar()`, `plt.scatter()`, `plt.hist()`, `sns.*`, etc. with Chinese strings
- User's code has Chinese inside `set_title()`, `set_xlabel()`, `set_ylabel()`, `legend()`, `annotate()`, `text()`, `suptitle()`
- Any `.ipynb` cell being created that contains both matplotlib and Chinese characters

## Font Fallback Order

```
'Microsoft YaHei' > 'SimHei' > 'Arial Unicode MS'
```

- **Microsoft YaHei** (微软雅黑): Best choice on Windows, clean and modern
- **SimHei** (黑体): Fallback, available on most Windows systems
- **Arial Unicode MS**: Broad Unicode coverage, works on macOS too

## Example

### Before (will show tofu □□□)

```python
fig, ax = plt.subplots()
ax.set_title("5-Fold 交叉验证 RMSE 分布")
ax.set_xlabel("预测销售额")
plt.show()
```

### After (correct)

```python
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots()
ax.set_title("5-Fold 交叉验证 RMSE 分布")
ax.set_xlabel("预测销售额")
plt.show()
```

## Check Before Output

Before finalizing any code with matplotlib + Chinese, verify:
1. `plt.rcParams['font.sans-serif']` is set before any `plt.subplots()` or `plt.figure()` call
2. `plt.rcParams['axes.unicode_minus'] = False` is included (prevents minus sign issues)
3. The rcParams lines are placed after `import matplotlib.pyplot as plt` but before any plotting