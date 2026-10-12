"""'Never calculate in the API layer': no Decimal or floats anywhere in roundup_api, and no arithmetic at all
in the service layer that builds engine inputs and outputs (counters and timers elsewhere are not finance)."""

import ast
import pathlib

import roundup_api

PKG = pathlib.Path(roundup_api.__file__).parent


def _tree(name):
    return ast.parse((PKG / name).read_text())


def test_no_decimal_or_float_in_api():
    for path in PKG.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            assert not (isinstance(node, ast.Constant) and isinstance(node.value, float)), path.name
            assert not (isinstance(node, ast.Name) and node.id in ("float", "Decimal")), path.name
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
                assert "decimal" not in names and "fractions" not in names, path.name


def test_service_layer_has_no_arithmetic():
    for node in ast.walk(_tree("service.py")):
        assert not isinstance(node, (ast.BinOp, ast.AugAssign)), getattr(node, "lineno", "?")
