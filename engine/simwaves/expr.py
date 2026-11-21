"""Safe expression language: a whitelisted subset of Python syntax translated to SymPy.

Nothing is ever passed to eval(). Allowed: numbers, names known to the scene, + - * / ** ^,
calls to engine functions, comparisons (only where a relation is expected), and unit
brackets such as 10[cm]. Size limits stop runaway computation from scene text.
When dimension checking is on, sums and comparisons must agree in dimension.
"""
import ast
import operator
import re

import sympy as sp

from .errors import SceneError
from .units import DIMLESS, unit_from_ast

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow}
_CMP = {ast.Eq: "==", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
MAX_TEXT = 2000
MAX_INT = 10 ** 30
MAX_EXP = 100


class Ref:
    """A reference to a scene object (medium, wave, emitter) used as a function argument."""

    def __init__(self, name, obj):
        self.name, self.obj = name, obj

    def __repr__(self):
        return self.name


class Rel:
    def __init__(self, op, lhs, rhs):
        self.op, self.lhs, self.rhs = op, lhs, rhs


def _parse(text):
    src = str(text).replace("^", "**")
    if len(src) > MAX_TEXT:
        raise SceneError("expression too long")
    try:
        return src, ast.parse(src, mode="eval")
    except SyntaxError as exc:
        raise SceneError(f"cannot parse expression: {text!r}") from exc


def translate(text, ctx, allow_rel=False, check_dims=False):
    src, tree = _parse(text)
    out = _Tr(src, ctx, allow_rel).run(tree.body)
    if check_dims:
        _Dim(src, ctx).node(tree.body)
    return out


def dimension_of(text, ctx):
    """Dimension tuple of an expression (None if unknown)."""
    src, tree = _parse(text)
    return _Dim(src, ctx).node(tree.body)


def show_dim(d):
    return "?" if d is None else _show(d)


def _float_literal(seg):
    m = re.fullmatch(r"[0-9.]+(?:[eE]([+-]?\d+))?", seg or "")
    if not m or len(seg) > 40 or (m.group(1) and abs(int(m.group(1))) > 300):
        raise SceneError(f"number literal out of range: {seg!r}")
    return sp.Rational(seg)


class _Tr:
    def __init__(self, src, ctx, allow_rel):
        self.src, self.ctx, self.allow_rel = src, ctx, allow_rel

    def run(self, node):
        out = self.node(node, top=True)
        if isinstance(out, Ref):
            raise SceneError(f"'{out.name}' is an object, not a value; call a function on it")
        return out

    def val(self, node):
        out = self.node(node)
        if isinstance(out, (Ref, list)):
            raise SceneError(f"expected a value in {self.src!r}")
        return out

    def node(self, n, top=False):
        if isinstance(n, ast.Constant):
            if isinstance(n.value, bool):
                return sp.true if n.value else sp.false
            if isinstance(n.value, int):
                if abs(n.value) > MAX_INT:
                    raise SceneError("integer literal too large")
                return sp.Integer(n.value)
            if isinstance(n.value, float):
                return _float_literal(ast.get_source_segment(self.src, n))
            raise SceneError(f"literal not allowed: {n.value!r}")
        if isinstance(n, ast.Name):
            return self.ctx.name(n.id)
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            a, b = self.val(n.left), self.val(n.right)
            if isinstance(a, sp.Tuple) or isinstance(b, sp.Tuple):
                raise SceneError("a list result (such as resonances(...)) cannot be used in "
                                 "arithmetic; use count(...) on it, or observe it on its own")
            if isinstance(n.op, ast.Pow) and b.is_number and abs(sp.N(b)) > MAX_EXP:
                raise SceneError(f"exponent too large in {self.src!r}")
            return _BIN[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = self.val(n.operand)
            if isinstance(v, sp.Tuple):
                raise SceneError("a list result (such as resonances(...)) cannot be negated")
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.Subscript):
            if isinstance(n.slice, ast.Constant):
                raise SceneError(f"indexing such as [1] is not supported in {self.src!r}; "
                                 f"brackets hold units. Use min(...), max(...) or count(...) on lists")
            _no_celsius(n.slice, self.src)
            factor, _ = unit_from_ast(n.slice)
            base = self.val(n.value)
            if isinstance(base, sp.Tuple):
                raise SceneError("a list result cannot take a unit")
            return base * factor
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name):
                raise SceneError("only plain function names may be called")
            if any(k.arg is None for k in n.keywords) or any(isinstance(a, ast.Starred) for a in n.args):
                raise SceneError("*args / **kwargs not allowed")
            if n.func.id == "nearest" and n.args and _is_in(n.args[0]):
                if n.keywords:
                    raise SceneError("nearest() takes no keyword arguments")
                return self.ctx.call("nearest", self._nearest_in(n.args), {})
            args = [self.node(a) for a in n.args]
            kwargs = {k.arg: self.node(k.value) for k in n.keywords}
            if n.func.id == "limit":
                # positional only, so that the written text of the expression and the point is
                # always seen (a keyword form would bypass the checks below)
                if n.keywords or len(n.args) != 3:
                    raise SceneError("limit(): write it as limit(expr, var, value), three arguments in that "
                                     "order, without keywords")
                checked = [n.args[0], n.args[2]]
                # an arbitrary function (functions:) is not a number, even where it cancels
                # (F(0) - F(0) -> 0) or has no symbols (F(1))
                for nd in checked:
                    for x in ast.walk(nd):
                        if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and \
                                x.func.id in getattr(self.ctx, "functions", {}):
                            raise SceneError(f"limit(): {x.func.id} is an arbitrary function, not a number; "
                                             f"apart from its variable, everything in a limit must be a number")
                # the symbols named in the expression and the point as written: SymPy's
                # automatic simplification (log(c) - log(c) -> 0) must not hide one
                kwargs["_written"] = tuple(self._named_symbols(checked))
            return self.ctx.call(n.func.id, args, kwargs)
        if isinstance(n, ast.Compare):
            if not (top and self.allow_rel):
                raise SceneError(f"comparison not allowed here: {self.src!r}")
            rels, left = [], self.val(n.left)
            for op, right in zip(n.ops, n.comparators):
                if type(op) not in _CMP:
                    raise SceneError("unsupported comparison")
                r = self.val(right)
                rels.append(Rel(_CMP[type(op)], left, r))
                left = r
            return rels
        raise SceneError(f"not allowed in expressions: {type(n).__name__} in {self.src!r}")

    def _named_symbols(self, nodes):
        """The free symbols of every name written in these nodes: not function names, and not
        unit names inside brackets (2[m] is two metres, whatever 'm' names elsewhere)."""
        out = set()

        def walk(x):
            if isinstance(x, ast.Subscript):       # value[unit]: the unit is parsed as a unit
                walk(x.value)
                return
            if isinstance(x, ast.Call):            # the function name is not a value
                for a in list(x.args) + [k.value for k in x.keywords]:
                    walk(a)
                return
            if isinstance(x, ast.Name):
                try:
                    v = self.ctx.name(x.id)
                except SceneError:
                    return
                if isinstance(v, sp.Basic):
                    out.update(v.free_symbols)
                return
            for child in ast.iter_child_nodes(x):
                walk(child)
        for nd in nodes:
            walk(nd)
        return out

    def _nearest_in(self, nodes):
        """nearest(x in u, a, b, ...): x converted to the unit u (checked as for 'observe ...
        in u'); a bare-number option is read in u, an option with a unit is converted to u."""
        cmp_ = nodes[0]
        x_src = ast.get_source_segment(self.src, cmp_.left)
        u_src = ast.get_source_segment(self.src, cmp_.comparators[0])
        factor, offset, udim = self.ctx.unit_for_nearest(x_src, u_src)
        out = [(self.val(cmp_.left) - offset) / factor]
        for o in nodes[1:]:
            if _is_in(o):
                raise SceneError("nearest(x in u, ...): only the value takes 'in u'; options are numbers in u "
                                 "or quantities with units")
            d = _Dim(self.src, self.ctx).node(o)
            v = self.val(o)
            o_src = ast.get_source_segment(self.src, o)
            if d is None and not sp.sympify(v).is_number:
                # an unknown or symbol whose unit no field fixes: check it as 'x in u' would
                # (its recorded dimension, or the facts that use it); never read it as a number in u
                f_o, off_o, _ = self.ctx.unit_for_nearest(o_src, u_src)
                out.append((v - off_o) / f_o)
            elif d in (None, DIMLESS):
                out.append(v)                      # a printed number, read in the unit u
            elif d != udim:
                raise SceneError(f"nearest(): option {o_src!r} has dimension {_show(d)}, not that of {u_src}")
            else:
                out.append((v - offset) / factor)
        return out


def _no_celsius(unit_node, src):
    """degC in a unit bracket is ambiguous: 20[degC] could be a temperature (293.15 K) or a
    difference (20 K). It is refused; a scene field ('30 degC') and 'x in degC' are not."""
    if any(isinstance(x, ast.Name) and x.id == "degC" for x in ast.walk(unit_node)):
        raise SceneError(f"degC inside unit brackets is ambiguous (a temperature or a temperature "
                         f"difference) in {src!r}: write temperatures in K, e.g. 293.15[K], or a "
                         f"difference as 20[K]; results can still be given 'in degC'")


def _is_in(node):
    return isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In)


def _pure_number(node):
    """True for a literal number such as 0, (0), -0 or 2*0: no names, calls or units."""
    return all(isinstance(x, (ast.Constant, ast.UnaryOp, ast.BinOp, ast.operator, ast.unaryop))
               and not (isinstance(x, ast.Constant) and isinstance(x.value, bool))
               for x in ast.walk(node))


def _dmul(a, b, sign=1):
    return tuple(x + sign * y for x, y in zip(a, b))


class _Dim:
    """Dimension checker. A dimension is a tuple (L, M, T, K); None means 'not known'
    (free symbols and bare zero carry no dimension). 'obj' marks object references."""

    def __init__(self, src, ctx):
        self.src, self.ctx = src, ctx

    def fail(self, a, b, what):
        hint = ""
        if re.search(r"\d\s*/\s*\d+(\.\d+)?\[", self.src):
            hint = (" (note: a unit bracket binds tighter than '/', so 3/2[m] means 3/(2 m); "
                    "write (3/2)[m] or 1.5[m])")
        raise SceneError(f"dimension mismatch in {what} of {self.src!r}: {_show(a)} vs {_show(b)}{hint}")

    def same(self, a, b, what):
        if a is not None and b is not None and a != b:
            self.fail(a, b, what)
        return a if a is not None else b

    def node(self, n):
        if isinstance(n, ast.Constant):
            if isinstance(n.value, bool) or n.value == 0:
                return None
            return DIMLESS
        if isinstance(n, ast.Name):
            return self.ctx.name_dim(n.id)
        if isinstance(n, ast.UnaryOp):
            return self.node(n.operand)
        if isinstance(n, ast.Subscript):
            v = self.node(n.value)
            _no_celsius(n.slice, self.src)
            _, ud = unit_from_ast(n.slice)
            if v is None and _pure_number(n.value):
                v = DIMLESS                # '0[m]': a written zero takes the bracket's unit
            return None if v is None else _dmul(v, ud)
        if isinstance(n, ast.BinOp):
            a, b = self.node(n.left), self.node(n.right)
            if isinstance(n.op, (ast.Add, ast.Sub)):
                return self.same(a, b, "a sum")
            if isinstance(n.op, ast.Mult):
                return None if a is None or b is None else _dmul(a, b)
            if isinstance(n.op, ast.Div):
                return None if a is None or b is None else _dmul(a, b, -1)
            if isinstance(n.op, ast.Pow):
                if b not in (None, DIMLESS):
                    raise SceneError(f"exponent must be dimensionless in {self.src!r}")
                if a is None or a == DIMLESS:
                    return a
                e = _Tr(self.src, self.ctx, False).val(n.right)
                if not e.is_Rational:
                    raise SceneError(f"a dimensional base needs a numeric exponent in {self.src!r}")
                return tuple(x * e for x in a)
        if isinstance(n, ast.Call):
            # 'x in u' inside nearest() is checked when it is translated (_Tr._nearest_in)
            args = [None if _is_in(a) else self.node(a) for a in n.args]
            kwargs = {k.arg: self.node(k.value) for k in n.keywords}
            return self.ctx.call_dim(n.func.id, args, kwargs, n, self)
        if isinstance(n, ast.Compare):
            left = self.node(n.left)
            for c in n.comparators:
                r = self.node(c)
                self.same(left, r, "a comparison")
                left = r if r is not None else left
            return None
        return None


def _show(d):
    names = "m kg s K".split()
    parts = [f"{u}^{p}" if p != 1 else u for u, p in zip(names, d) if p != 0]
    return "*".join(parts) or "dimensionless"
