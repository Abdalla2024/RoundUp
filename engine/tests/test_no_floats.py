"""R-0.5: no float literals or float() calls in the engine or scenario-generator packages."""

import ast
import pathlib

import roundup_engine
import roundup_scenarios

PKGS = [pathlib.Path(roundup_engine.__file__).parent, pathlib.Path(roundup_scenarios.__file__).parent]


def test_no_floats_in_engine_source():
    offenders = []
    for path in [p for pkg in PKGS for p in pkg.rglob("*.py")]:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                offenders.append(f"{path.name}:{node.lineno} float literal")
            if isinstance(node, ast.Name) and node.id == "float":
                offenders.append(f"{path.name}:{node.lineno} float name")
            if isinstance(node, ast.Attribute) and node.attr in ("from_float", "create_decimal_from_float"):
                offenders.append(f"{path.name}:{node.lineno} {node.attr}")
    assert not offenders, offenders
