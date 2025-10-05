#!/usr/bin/env python3
import sys
import os
from typing import Literal
import subprocess
from enum import Enum

Operator = Literal["=", ">=", "<=", ">", "<"]


class Dependency:
    name: str
    operator: Operator
    version: str
    path: str | None
    def __init__(self, name, operator, version, path):
        self.name = name
        self.operator = operator
        self.version = version
        self.path = path
    def __repr__(self):
        return f"{self.name}{self.operator}{self.version}"


class BoxedInteger:
    box: int
    def __init__(self, start: int):
        self.box = start
    def increment(self):
        self.box += 1
    def read(self):
        return self.box
    def __str__(self):
        return str(self.read()).rjust(4, "0") + ": "


class RPMLibraryStatus(Enum):
    NOT_AVAILABLE = 1
    IMPORTED = 2


class RPM:
    name: str
    version: str
    dependencies: list[Dependency]
    path: str

    def __init__(self, name, version, dependencies, path):
        self.name = name
        self.version = version
        self.dependencies = dependencies
        self.path = path
    

def compare_rpm_versions(installed_path: str, required_path: str, operator: Operator) -> bool:
    try:
        import rpm # type: ignore
    except ImportError:
        return True
    with open(installed_path, 'rb') as f:
        hdr_installed = rpm.hdr(f)
    
    with open(required_path, 'rb') as f:
        hdr_required = rpm.hdr(f)
    
    installed_evr = (
        hdr_installed['epoch'] or 0,
        hdr_installed['version'],
        hdr_installed['release']
    )
    
    required_evr = (
        hdr_required['epoch'] or 0,
        hdr_required['version'],
        hdr_required['release']
    )
    
    cmp_result = rpm.labelCompare(installed_evr, required_evr)
    
    if operator == "=":
        return cmp_result == 0
    elif operator == ">=":
        return cmp_result >= 0
    elif operator == "<=":
        return cmp_result <= 0
    elif operator == ">":
        return cmp_result > 0
    elif operator == "<":
        return cmp_result < 0
    return False


def print_help() -> None:
    script_name = os.path.basename(sys.argv[0])
    print(f"Usage: {script_name} <directory_path> <root_rpm>")


def query_rpm(path: str, query: str) -> str:
    result = subprocess.run(
        ["rpm", "-qp", "--queryformat", query, path],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"command failed with exit code {result.returncode}: rpm -qp --queryformat {query} {path}")
        sys.exit(1)
    return result.stdout


def tokenise_dependency(dependency: str) -> Dependency:
    cur = 0
    # Get RPM name
    while cur < len(dependency) and dependency[cur] not in [" ", "=", ">", "<"]:
        cur += 1
    dependency_name = dependency[0 : cur]
    # If name only, return early
    if cur >= len(dependency):
        return Dependency(dependency_name, ">=", "0.0", None)
    # Parse operator
    if dependency[cur] == ' ':
        cur += 1
    operator_start = cur
    while dependency[cur] in ["=", "<", ">"]:
        cur += 1
    operator = dependency[operator_start : cur]
    # Version is the remainder of the string
    if dependency[cur] == ' ':
        cur += 1
    version = dependency[cur :]
    return Dependency(dependency_name, operator, version, None)


def get_rpm_dependencies(path: str) -> list[Dependency]:
    result = subprocess.run(
        ["rpm", "-qpR", path],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"command failed with exit code {result.returncode}: rpm -qpR {path}")
        sys.exit(1)
    all_dependencies: str = result.stdout
    dependency_list = all_dependencies.splitlines()
    return [tokenise_dependency(d) for d in dependency_list]


def build_dict(directory: str) -> dict[str, RPM]:
    ret: dict[str, RPM] = {}
    for fname in os.listdir(directory):
        path = os.path.join(directory, fname)
        if (os.path.isfile(path) and fname.lower().endswith(".rpm")):
            rpmname = query_rpm(path, "%{NAME}").strip()
            rpmversion = query_rpm(path, "%{VERSION}").strip()
            dependencies = get_rpm_dependencies(path)
            if rpmname in ret:
                print(f"Found duplicate of {fname}, aborting")
                sys.exit(1)
            ret[rpmname] = RPM(rpmname, rpmversion, dependencies, path)
    return ret


def clean_dict(
        dag: dict[str, RPM],
    ) -> None:
    for name, rpm in dag.items():
        cleaned_dependencies = []
        for dependency in rpm.dependencies:
            if dependency.name not in dag: continue
            if dependency.path is None:
                print(f"Error: dependency {dependency} should've had a path, but it was None")
                sys.exit(1)
            if not compare_rpm_versions(
                dag[dependency.name].path,
                dependency.path or '',
                dependency.operator
            ):
                installed_version = dag[dependency.name].version
                print(f"Warning: {name} requires {dependency.name} {dependency.operator} {dependency.version}, but found version {installed_version}")
            cleaned_dependencies.append(dependency)
            dependency.path = dag[dependency.name].path
        rpm.dependencies = cleaned_dependencies


def walk(dag: dict[str, RPM], root_rpm: str) -> None:
    return walk_impl(dag, root_rpm, BoxedInteger(0), "", {})


def walk_impl(
        dag: dict[str, RPM],
        current_rpm: str,
        line_num: BoxedInteger,
        padding: str,
        visited: dict[str, int],
        is_last: bool = True
    ) -> None:
    if current_rpm not in dag:
        return
    line_num.increment()
    
    prefix = padding + ('└─ ' if is_last else '├─ ')
    
    if current_rpm in visited:
        print(f"{str(line_num)}{prefix}{current_rpm} (goto line {visited[current_rpm]})")
    else:
        dependencies = dag[current_rpm].dependencies
        visited[current_rpm] = line_num.read()
        
        this_line = f"{str(line_num)}{prefix}{current_rpm}"
        if len(dependencies) == 0: this_line += " (no dependencies)"
        print(this_line)
        
        for i, dependency in enumerate(dependencies):
            is_last_dep = (i == len(dependencies) - 1)
            new_padding = padding + ('   ' if is_last else '│  ')
            walk_impl(dag, dependency.name, line_num, new_padding, visited, is_last_dep)


def check_tools() -> None:
    if subprocess.run(
        ["rpm", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ).returncode != 0:
        print("Error: command line tool `rpm` is not installed")
        sys.exit(1)

def main() -> None:
    if len(sys.argv) != 3:
        print(f"Expected 2 arguments, provided {len(sys.argv) - 1}.")
        print_help()
        sys.exit(1)

    dir_path = sys.argv[1]
    root_rpm_path = sys.argv[2]

    if not os.path.isdir(dir_path):
        print(f"Error: '{dir_path}' is not a valid directory.\n")
        print_help()
        sys.exit(1)

    if not os.path.isfile(root_rpm_path):
        print(f"Error: '{root_rpm_path}' is not a valid file.\n")
        print_help()
        sys.exit(1)

    if not root_rpm_path.endswith(".rpm"):
        print(f"Error: second argument must be a .rpm file, got {root_rpm_path}")
        sys.exit(1)
    
    check_tools()

    root_rpm_name = query_rpm(root_rpm_path, "%{NAME}")

    dependency_dag = build_dict(dir_path)
    clean_dict(dependency_dag)
    walk(dependency_dag, root_rpm_name)


if __name__ == "__main__":
    main()
