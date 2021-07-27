import os
import sys
import re
from collections import defaultdict


def _is_source_file(f):
    return f.endswith(".kt") or f.endswith(".java")


def _gather_files(rootdir):
    all_files = []
    for subdir, _, files in os.walk(rootdir):
        if "/test/" not in subdir:
            all_files += [os.path.join(subdir, f) for f in files if _is_source_file(f)]
    return all_files


def _target_pkg(imp, all_pkgs: set[str]):
    partial = imp
    while True:
        if partial in all_pkgs:
            return partial
        next = partial.rsplit(".", 1)[0]
        if next == partial or len(next) == 0:
            return None
        partial = next


def _gather_imports(files):
    imports = defaultdict(set)

    for file in files:
        pkg = None
        my_imports = []

        with open(file) as f:
            for line in f.readlines():
                match = re.match("package ([^;]+);?", line)
                if match is not None:
                    pkg = match.group(1)

                match = re.match("import (?:static )?([^;]+);?", line)
                if match is not None:
                    my_imports.append(match.group(1))

        if pkg is not None:
            imports[pkg].update(my_imports)

    return imports


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


def _render_graph(deps, fh):
    mapping = {}
    for i, src in enumerate(deps.keys()):
            mapping[src] = i

    fh.write("digraph D {\n")

    for src, i in mapping.items():
        fh.write(f"  {i} [label=\"{_short_pkg_name(src)}\"]\n")

    for src, targets in deps.items():
        for t in targets:
            fh.write(f"  {mapping[src]} -> {mapping[t]}\n")

    fh.write("}\n")


def _main():
    rootdir = sys.argv[1]
    files = _gather_files(rootdir)
    imports = _gather_imports(files)
    deps = _resolve_deps(imports)
    _render_graph(deps, sys.stdout)


if __name__ == "__main__":
    _main()