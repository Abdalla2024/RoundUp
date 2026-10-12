"""R-0.5: no float literals or float() calls in the engine package."""

import ast
import pathlib

import roundup_engine

PKG = pathlib.Path(roundup_engine.__file__).parent


def test_no_floats_in_engine_source():
    offenders = []
    for path in PKG.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                offenders.append(f"{path.name}:{node.lineno} float literal")
            if isinstance(node, ast.Name) and node.id == "float":
                offenders.append(f"{path.name}:{node.lineno} float name")
            if isinstance(node, ast.Attribute) and node.attr in ("from_float", "create_decimal_from_float"):
                offenders.append(f"{path.name}:{node.lineno} {node.attr}")
    assert not offenders, offenders
