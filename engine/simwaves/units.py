"""Units: parse unit text into an exact SI factor plus a dimension vector (L, M, T, K)."""
import ast
import re

import sympy as sp

from .errors import SceneError


def dim(L=0, M=0, T=0, K=0):
    return (L, M, T, K)


DIMLESS = dim()
LENGTH, MASS, TIME, TEMP = dim(L=1), dim(M=1), dim(T=1), dim(K=1)
FORCE = dim(1, 1, -2)
_R = sp.Rational

UNITS = {
    "m": (1, LENGTH), "cm": (_R(1, 100), LENGTH), "mm": (_R(1, 1000), LENGTH), "km": (1000, LENGTH),
    "um": (_R(1, 10 ** 6), LENGTH), "μm": (_R(1, 10 ** 6), LENGTH),   # micrometre (the micro sign normalises to mu)
    "nm": (_R(1, 10 ** 9), LENGTH),
    "h": (3600, TIME), "kmph": (_R(5, 18), dim(1, 0, -1)),   # hour (see split_quantity), km/h
    "s": (1, TIME), "ms": (_R(1, 1000), TIME), "us": (_R(1, 10 ** 6), TIME), "ns": (_R(1, 10 ** 9), TIME),
    "kg": (1, MASS), "g": (_R(1, 1000), MASS),
    "N": (1, FORCE), "Pa": (1, dim(-1, 1, -2)), "J": (1, dim(2, 1, -2)), "mJ": (_R(1, 1000), dim(2, 1, -2)),
    "W": (1, dim(2, 1, -3)), "mW": (_R(1, 1000), dim(2, 1, -3)), "kW": (1000, dim(2, 1, -3)),
    "kHz": (1000, dim(T=-1)), "MHz": (10 ** 6, dim(T=-1)), "GHz": (10 ** 9, dim(T=-1)), "kPa": (1000, dim(-1, 1, -2)), "Hz": (1, dim(T=-1)),
    "rad": (1, DIMLESS), "deg": (sp.pi / 180, DIMLESS),
    "K": (1, TEMP), "degC": (1, TEMP),
    "mol": (1, DIMLESS),      # amount of substance is treated as a pure count
}
CELSIUS_OFFSET = _R(27315, 100)


def _mul(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _pow(a, n):
    return tuple(x * n for x in a)


def unit_from_ast(node):
    """Return (factor, dimension) for a unit expression such as kg/m**3 or 1/K."""
    if isinstance(node, ast.Name):
        if node.id not in UNITS:
            raise SceneError(f"unknown unit '{node.id}'")
        f, d = UNITS[node.id]
        return sp.sympify(f), d
    if isinstance(node, ast.Constant) and node.value == 1:
        return sp.Integer(1), DIMLESS
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            base = unit_from_ast(node.left)
            n = node.right
            sign = 1
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
                sign, n = -1, n.operand
            if not (isinstance(n, ast.Constant) and isinstance(n.value, int)):
                raise SceneError("unit exponents must be whole numbers")
            e = sign * n.value
            if abs(e) > 12:
                raise SceneError("unit exponent too large")
            return base[0] ** e, _pow(base[1], e)
        a, b = unit_from_ast(node.left), unit_from_ast(node.right)
        if isinstance(node.op, ast.Mult):
            return a[0] * b[0], _mul(a[1], b[1])
        if isinstance(node.op, ast.Div):
            return a[0] / b[0], _mul(a[1], _pow(b[1], -1))
    raise SceneError("malformed unit expression")


def _degc_power(node):
    """The net power of degC in a unit expression (0 if it does not occur)."""
    if isinstance(node, ast.Name):
        return 1 if node.id == "degC" else 0
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            n = node.right
            sign = -1 if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) else 1
            n = n.operand if sign == -1 else n
            return _degc_power(node.left) * sign * (n.value if isinstance(n, ast.Constant) else 0)
        a, b = _degc_power(node.left), _degc_power(node.right)
        return a - b if isinstance(node.op, ast.Div) else a + b
    return 0


def parse_unit(text):
    try:
        node = ast.parse(text.replace("^", "**"), mode="eval").body
    except SyntaxError as exc:
        raise SceneError(f"malformed unit '{text}'") from exc
    factor, d = unit_from_ast(node)
    # degC carries the 273.15 K offset only when written exactly as `degC` (the offset is
    # applied by that spelling): any other spelling of an absolute Celsius temperature, such
    # as (degC) or degC^1, would silently lose it, so it is refused (review m15b, D4-5).
    # Inside a compound unit (1/degC, J/degC, degC/s) degC is a temperature difference, where
    # no offset applies, and it keeps its meaning.
    p = _degc_power(node)
    if p != 0 and (abs(p) > 1 or (d == TEMP and text.strip() != "degC")):
        raise SceneError(f"unit '{text}': write an absolute Celsius temperature exactly as degC (e.g. 27 degC), "
                         f"or give it in K")
    return factor, d


_UNIT_TOKEN = re.compile(r"^[A-Za-z0-9_*/^().\-µμ]+$")
# Unit names that are too often a variable to be read as a unit when they stand alone
# after a value ('rho g h' is not 'rho g' hours); they still work inside a compound unit
# such as km/h, or in brackets, 2[h].
_NOT_ALONE = {"h"}


def split_quantity(text):
    """Split '3*pi rad/s' into ('3*pi', 'rad/s', factor, dim). No unit -> (text, None, 1, None)."""
    text = str(text).strip()
    m = re.match(r"^(.*\S)\s+(\S+)$", text)
    if m and _UNIT_TOKEN.match(m.group(2)) and m.group(2) not in _NOT_ALONE:
        try:
            factor, d = parse_unit(m.group(2))
            return m.group(1), m.group(2), factor, d
        except SceneError:
            if "degC" in m.group(2):
                raise                  # a Celsius spelling that would lose its offset (D4-5)
    return text, None, sp.Integer(1), None
