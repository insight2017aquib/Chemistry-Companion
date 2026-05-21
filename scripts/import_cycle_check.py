import ast
from pathlib import Path

root = Path(__file__).resolve().parent.parent
py_files = [p for p in root.rglob('*.py') if 'site-packages' not in str(p)]
imports = {}

prefixes = ('core', 'api', 'services', 'spectra', 'exports', 'reports', 'database')
for p in py_files:
    module = str(p.relative_to(root)).replace('\\', '/').removesuffix('.py')
    if module.endswith('/__init__'):
        module = module[: -len('/__init__')]
    with p.open('r', encoding='utf-8') as fh:
        try:
            tree = ast.parse(fh.read(), filename=str(p))
        except SyntaxError:
            continue
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                if n.name.startswith(prefixes):
                    mods.add(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith(prefixes):
                mods.add(node.module)
    imports[module] = sorted(mods)

# detect cycles
visited = {}
stack = []
cycles = []

def dfs(node):
    visited[node] = 1
    stack.append(node)
    for neigh in imports.get(node, []):
        if neigh not in imports:
            continue
        if visited.get(neigh, 0) == 0:
            dfs(neigh)
        elif visited[neigh] == 1:
            cycle = stack[stack.index(neigh):] + [neigh]
            cycles.append(cycle)
    stack.pop()
    visited[node] = 2

for node in imports:
    if visited.get(node, 0) == 0:
        dfs(node)

print('MODULE_COUNT', len(imports))
print('CYCLE_COUNT', len(cycles))
for cycle in cycles:
    print('CYCLE:', ' -> '.join(cycle))
print('---')
for module, deps in sorted(imports.items()):
    if deps:
        print(f'{module} -> {deps}')
