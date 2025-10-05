#!/usr/bin/env python3
import sys
import os
from typing import Literal
import subprocess
from enum import Enum


class Constraint:
    rpm_name: str
    operator: str
    desired_evr: str
    rpm_path: str | None
    def __init__(
        self,
        rpm_name: str,
        operator: str,
        desired_evr: str,
        rpm_path: str | None
    ) -> None:
        self.rpm_name = rpm_name
        self.operator = operator
        self.desired_evr = desired_evr
        self.rpm_path = rpm_path
    def __repr__(self) -> str:
        return f"{self.rpm_name} {self.operator} {self.desired_evr}"


class BoxedInteger:
    box: int
    def __init__(self, start: int):
        self.box = start
    def increment(self) -> None:
        self.box += 1
    def read(self) -> int:
        return self.box
    def __str__(self) -> str:
        return str(self.read()).rjust(4, "0") + ": "


class RPM:
    name: str
    version: str
    epoch: str
    release: str
    constraints: list[Constraint]
    path: str

    def __init__(
        self,
        name: str,
        version: str,
        epoch: str,
        release: str,
        constraints: list[Constraint],
        path: str
    ):
        self.name = name
        self.version = version
        self.epoch = epoch
        self.release = release
        self.constraints = constraints
        self.path = path
    

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


def tokenise_dependency(dependency: str) -> Constraint:
    cur = 0
    # Get RPM name
    while cur < len(dependency) and dependency[cur] not in [" ", "=", ">", "<"]:
        cur += 1
    dependency_name = dependency[0 : cur]
    # If name only, return early
    if cur >= len(dependency):
        return Constraint(dependency_name, ">=", "0.0", None)
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
    return Constraint(dependency_name, operator, version, None)


def get_rpm_dependencies(path: str) -> list[Constraint]:
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
            rpmepoch = query_rpm(path, "${EPOCH}").strip()
            rpmrelease = query_rpm(path, "${RELEASE}").strip()
            dependencies = get_rpm_dependencies(path)
            if rpmname in ret:
                print(f"Found duplicate of {fname}, aborting")
                sys.exit(1)
            ret[rpmname] = RPM(rpmname, rpmversion, rpmepoch, rpmrelease, dependencies, path)
    return ret


def clean_dict(
        dag: dict[str, RPM],
    ) -> None:
    for name, rpm in dag.items():
        cleaned_constraints = []
        for constraint in rpm.constraints:
            if constraint.rpm_name not in dag:
                continue
            constraint.rpm_path = dag[constraint.rpm_name].path
            cleaned_constraints.append(constraint)
        rpm.constraints = cleaned_constraints


def warn_version_mismatches(
        dag: dict[str, RPM]
    ) -> None:
    for name, rpm in dag.items():
        for constraint in rpm.constraints:
            local_copy_of_dependency: RPM = dag[constraint.rpm_name]
            local_copy_of_dependency_evr = (
                local_copy_of_dependency.epoch,
                local_copy_of_dependency.version,
                local_copy_of_dependency.release
            )
            # TODO: Somehow get EVR info from the constraint
    return None


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
        constraints = dag[current_rpm].constraints
        visited[current_rpm] = line_num.read()
        
        this_line = f"{str(line_num)}{prefix}{current_rpm}"
        if len(constraints) == 0: this_line += " (no dependencies)"
        print(this_line)
        
        for i, constraint in enumerate(constraints):
            is_last_dep = (i == len(constraints) - 1)
            new_padding = padding + ('   ' if is_last else '│  ')
            walk_impl(dag, constraint.rpm_name, line_num, new_padding, visited, is_last_dep)


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
    warn_version_mismatches(dependency_dag)
    walk(dependency_dag, root_rpm_name)


if __name__ == "__main__":
    main()
