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
    evr_string: str
    constraints: list[Constraint]
    path: str

    def __init__(
        self,
        name: str,
        version: str,
        epoch: str,
        release: str,
        evr_string: str,
        constraints: list[Constraint],
        path: str
    ):
        self.name = name
        self.version = version
        self.epoch = epoch
        self.release = release
        self.evr_string = evr_string
        self.constraints = constraints
        self.path = path
    

def print_help() -> None:
    script_name = os.path.basename(sys.argv[0])
    print(f"Usage: {script_name} <directory_path> <OPTIONAL: root_rpm>")


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


def get_rpm_constraints(path: str) -> list[Constraint]:
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
            rpmepoch = query_rpm(path, "%{EPOCH}").strip()
            rpmrelease = query_rpm(path, "%{RELEASE}").strip()
            rpmevr = query_rpm(path, "%{EVR}").strip()
            constraints = get_rpm_constraints(path)
            if rpmname in ret:
                print(f"Found duplicate of {fname}, aborting")
                sys.exit(1)
            ret[rpmname] = RPM(rpmname, rpmversion, rpmepoch, rpmrelease, rpmevr, constraints, path)
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


def compare_rpm_evr(
        local_evr: str,
        desired_evr: str,
        operator: str
    ) -> bool:

    # If the desired EVR does not specify a release, remove it from the local EVR
    if '-' not in desired_evr:
        local_evr = local_evr.rsplit('-', 1)[0]

    lua_code = f'print(rpm.vercmp("{local_evr}", "{desired_evr}"))'
    result = subprocess.run(
        ['rpm', '--eval', f'%{{lua:{lua_code}}}'],
        capture_output=True,
        text=True,
        check=True
    )
    cmp_result = int(result.stdout.strip())
    if operator == '<':
        return cmp_result < 0
    elif operator == '<=':
        return cmp_result <= 0
    elif operator == '=':
        return cmp_result == 0
    elif operator == '>=':
        return cmp_result >= 0
    elif operator == '>':
        return cmp_result > 0
    else:
        print(f"Invalid operator: {operator}")
        sys.exit(1)


def warn_version_mismatches(
        dag: dict[str, RPM],
        rpm_to_check: RPM,
    ) -> None:
    for constraint in rpm_to_check.constraints:
        local_copy_of_dependency: RPM = dag[constraint.rpm_name]
        if not compare_rpm_evr(
            local_copy_of_dependency.evr_string,
            constraint.desired_evr,
            constraint.operator
        ):
            print(f"Warning: {rpm_to_check.name} requires {constraint.rpm_name} version {constraint.operator} {constraint.desired_evr} but the local copy is version {local_copy_of_dependency.evr_string}.")


def walk(dag: dict[str, RPM], root_rpm: str | None) -> list[str]:
    line_number_map: dict[str, int] = {}
    current_line_number: BoxedInteger = BoxedInteger(0)
    if root_rpm:
        walk_impl(dag, root_rpm, current_line_number, "", line_number_map)
    else:
        # Do all RPMs
        for rpm_name in dag:
            # Do an RPM
            walk_impl(dag, rpm_name, current_line_number, "", line_number_map)
            # Add some whitespace between each one
            current_line_number.increment()
            print(str(current_line_number))
    # Return the RPMs which were included in the output
    return list(line_number_map.keys()) # RPMs which were visited


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
        print(f"{str(line_num)}{prefix}{current_rpm} (see line {visited[current_rpm]})")
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
    if len(sys.argv) not in [2,3]:
        print(f"Expected 1 or 2 arguments, provided {len(sys.argv) - 1}.")
        print_help()
        sys.exit(1)

    dir_path = sys.argv[1]
    root_rpm_path = None if len(sys.argv) < 3 else sys.argv[2]

    if not os.path.isdir(dir_path):
        print(f"Error: '{dir_path}' is not a valid directory.\n")
        print_help()
        sys.exit(1)

    if root_rpm_path and not os.path.isfile(root_rpm_path):
        print(f"Error: '{root_rpm_path}' is not a valid file.\n")
        print_help()
        sys.exit(1)

    if root_rpm_path and not root_rpm_path.endswith(".rpm"):
        print(f"Error: second argument must be a .rpm file, got {root_rpm_path}")
        sys.exit(1)
    
    check_tools()

    root_rpm_name: str | None = None if not root_rpm_path else query_rpm(root_rpm_path, "%{NAME}")

    dependency_dag = build_dict(dir_path)
    clean_dict(dependency_dag)
    visited_rpms = walk(dependency_dag, root_rpm_name)
    for rpm in visited_rpms:
        warn_version_mismatches(dependency_dag, dependency_dag[rpm])


if __name__ == "__main__":
    main()
