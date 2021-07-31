import os
import sys
import re
from collections import defaultdict


def _is_source_file(f):
    return (f.endswith(".kt") or f.endswith(".java")) and ("/test/" not in f and "/integTest/" not in f)


def _gather_files(rootdir):
    all_files = []
    for subdir, _, files in os.walk(rootdir):
        all_files += [os.path.join(subdir, f) for f in files]
    return [f for f in all_files if _is_source_file(f)]


def _target_pkg(imp, all_pkgs: set[str]):
    partial = imp
    while True:
        if partial in all_pkgs:
            return partial
        next = partial.rsplit(".", 1)[0]
        if next == partial or len(next) == 0:
            return None
        partial = next


def _module_of(pkg, file):
    pkg_file = pkg.replace(".", "/")
    module = os.path.dirname(file).removesuffix(pkg_file)
    return module


def _gather_imports(files, rootdir):
    imports = defaultdict(set)
    modules = defaultdict(set)

    for file in files:
        pkg = None
        my_imports = []

        with open(file) as f:
            for line in f.readlines():
                line = line.strip()

                match = re.match("package ([^;]+);?", line)
                if match is not None:
                    pkg = match.group(1)

                match = re.match("import (?:static )?([^;]+);?", line)
                if match is not None:
                    my_imports.append(match.group(1))

        if pkg is not None:
            imports[pkg].update(my_imports)
            modules[pkg].add(_module_of(pkg, os.path.relpath(file, rootdir)))

    return imports, modules


def _resolve_deps(imports):
    deps = {}

    for pkg, pkg_imports in imports.items():
        my_deps = set()

        for imp in pkg_imports:
            target = _target_pkg(imp, imports.keys())
            if target is not None and target != pkg:    # Avoid self-deps
                my_deps.add(target)

        deps[pkg] = my_deps

    return deps


def _short_pkg_name(pkg):
    parts = pkg.split(".")
    return ".".join([p[0] for p in parts[0:-1]]) + "." + parts[-1]


def _safe_pkg_name(pkg):
    return pkg.replace(".", "_").replace("$", "_")


def _render_graph(deps, modules, fh):
    other_pkgs = set()
    pkgs_by_module = defaultdict(set)
    for src in deps.keys():
        my_modules = modules[src]
        if len(my_modules) == 1:
            pkgs_by_module[list(my_modules)[0]].add(src)
        else:
            other_pkgs.add(src)

    fh.write(f"digraph D {{\n")
    fh.write(f"node [style=filled,fillcolor=white];\n")

    for pkg in deps.keys():
        fh.write(f"{_safe_pkg_name(pkg)} [label=\"{_short_pkg_name(pkg)}\"];\n")

    i = 0
    for module_name, module_pkgs in pkgs_by_module.items():
        fh.write(f"subgraph cluster_{i} {{\n")
        i = i + 1 

        for pkg in module_pkgs:
            for target in deps[pkg]:
                fh.write(f"{_safe_pkg_name(pkg)} -> {_safe_pkg_name(target)};\n")

        fh.write(f"label = \"{module_name}\";\n")
        fh.write(f"color = lightgrey;\n")
        fh.write(f"style = filled;\n")
        fh.write(f"}}\n")

    for pkg in other_pkgs:
        for target in deps[pkg]:
            fh.write(f"{_safe_pkg_name(pkg)} -> {_safe_pkg_name(target)};\n")

    fh.write("}\n")


def _main():
    rootdir = sys.argv[1]
    files = _gather_files(rootdir)
    imports, modules = _gather_imports(files, rootdir)
    deps = _resolve_deps(imports)
    _render_graph(deps, modules, sys.stdout)


if __name__ == "__main__":
    _main()