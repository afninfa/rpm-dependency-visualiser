#!/usr/bin/env python3
import sys
import os
from typing import Literal
import subprocess


# TODO: Make this a class
Dependency = tuple[str, Literal["=", ">="], str]


class BoxedInteger:
    box: list[int]
    def __init__(self, start: int): self.box = [start]
    def increment(self): self.box[0] += 1
    def read(self): return self.box[0]
    def __str__(self): return str(self.read()).ljust(4)


class RPM:
    name: str
    version: str
    dependencies: list[Dependency]

    def __init__(self, name: str, version: str, dependencies: list[Dependency]):
        self.name = name
        self.version = version
        self.dependencies = dependencies
    
    def __str__(self):
        ret = f"{self.name} {self.version}"
        for d in self.dependencies:
            ret += " " + str(d)
        return ret


def print_help() -> None:
    script_name = os.path.basename(sys.argv[0])
    print(f"Usage: {script_name} <directory_path> <root_rpm>")


def query_rpm(path: str, query: str) -> str:
    return subprocess.run(
        ["rpm", "-qp", "--queryformat", query, path],
        capture_output=True,
        text=True
    ).stdout


def tokenise_dependency(dependency: str) -> Dependency:
    cur = 0
    while cur < len(dependency) and dependency[cur] not in [" ", "=", ">", "<"]:
        cur += 1
    dependency_name = dependency[0 : cur]
    # TODO: operator and version number parsing
    return (dependency_name, "=", "0.0.0")


def get_rpm_dependencies(path: str) -> list[Dependency]:
    all_dependencies: str = subprocess.run(
        ["rpm", "-qpR", path],
        capture_output=True,
        text=True
    ).stdout
    dependency_list = all_dependencies.splitlines()
    return [tokenise_dependency(d) for d in dependency_list]


def build_dict(directory: str) -> dict[str, RPM]:
    ret: dict[str, RPM] = {}
    for fname in os.listdir(directory):
        path = os.path.join(directory, fname)
        if (os.path.isfile(path) and fname.lower().endswith(".rpm")):
            rpmname = query_rpm(path, "%{NAME}")
            rpmversion = query_rpm(path, "%{VERSION}")
            dependencies = get_rpm_dependencies(path)
            if rpmname in ret:
                print(f"Found duplicate of {fname}, aborting")
                sys.exit(1)
            ret[rpmname] = RPM(rpmname, rpmversion, dependencies)
    return ret


def walk(dag: dict[str, RPM], root_rpm: str) -> None:
    return walk_impl(dag, root_rpm, BoxedInteger(0), "", {})


def walk_impl(
        dag: dict[str, RPM],
        current_rpm: str,
        line_num: BoxedInteger,
        padding: str,
        visited: dict[str, int]
    ) -> None:
    if current_rpm not in dag:
        return
    line_num.increment()
    if current_rpm in visited:
        print(f"{str(line_num)}{padding}{current_rpm} (already expanded on line {visited[current_rpm]})")
    else:
        visited[current_rpm] = line_num.read()
        print(f"{str(line_num)}{padding}{current_rpm}")
        for dependency in dag[current_rpm].dependencies:
            walk_impl(dag, dependency[0], line_num, padding + "|  ", visited)


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Expected 2 arguments, provided {len(sys.argv) - 1}.")
        print_help()
        sys.exit(1)

    dir_path = sys.argv[1]
    root_rpm_path = sys.argv[2]

    if not os.path.isdir(dir_path) or not os.path.isfile(root_rpm_path):
        print(f"Error: '{dir_path}' is not a valid directory.\n")
        print_help()
        sys.exit(1)

    if not root_rpm_path.endswith(".rpm"):
        print(f"Error: second argument must be a .rpm file, got {root_rpm_path}")
        sys.exit(1)
    
    root_rpm_name = query_rpm(root_rpm_path, "%{NAME}")

    dependency_dag = build_dict(dir_path)
    walk(dependency_dag, root_rpm_name)


if __name__ == "__main__":
    main()
