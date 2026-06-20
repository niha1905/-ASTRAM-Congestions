import os
import json
import ast
from pathlib import Path

PROJECT_ROOT = r"g:/flipkart/track a"

# Helper to get all source files
def list_source_files():
    exts = {'.py', '.tsx', '.ts', '.js', '.jsx'}
    files = []
    for root, _, filenames in os.walk(PROJECT_ROOT):
        for name in filenames:
            if Path(name).suffix.lower() in exts:
                files.append(os.path.join(root, name))
    return files

# Build import graph for Python files
def build_python_imports(py_files):
    imports = {}
    for file in py_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=file)
            imported_modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.append(node.module)
            imports[file] = imported_modules
        except Exception as e:
            imports[file] = []
    return imports

# Save results
all_files = list_source_files()
py_files = [f for f in all_files if f.endswith('.py')]
python_imports = build_python_imports(py_files)

result = {
    "all_files": all_files,
    "python_imports": python_imports,
}

output_path = os.path.join(PROJECT_ROOT, 'project_scan_report.json')
with open(output_path, 'w', encoding='utf-8') as out:
    json.dump(result, out, indent=2)

print(f"Report written to {output_path}")
