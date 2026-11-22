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


def translate(text, ctx, allow_rel=False, check_dims=False, collect=False):
    """Translate an expression. While it is read, every log, root, power, division, tan,
    asin/acos and wave value at a point records the condition it needs (see _note) in a list
    kept beside the value, so that no SymPy simplification can cancel it. Each reading has
    its own list; with collect=True it is left in ctx.last_obligations for the caller to
    check (observe after the solve, facts as constraints)."""
    src, tree = _parse(text)
    sinks = _sinks(ctx)
    sinks.append([])
    try:
        out = _Tr(src, ctx, allow_rel).run(tree.body)
    finally:
        got = sinks.pop()
    if collect:
        ctx.last_obligations = got
    if check_dims:
        _Dim(src, ctx).node(tree.body)
    return out


def _sinks(ctx):
    s = getattr(ctx, "_obligation_sinks", None)
    if s is None:
        s = []
        try:
            ctx._obligation_sinks = s
        except AttributeError:
            pass
    return s


def _note(ctx, kind, g):
    """Record that g must be 'positive', 'nonneg', 'nonzero' or in [-1, 1] ('unit') for the
    expression being read to be real and finite. Conditions that already hold are dropped."""
    sinks = getattr(ctx, "_obligation_sinks", None)
    if not sinks:
        return
    g = sp.sympify(g)
    if holds(kind, g) is True:
        return
    sinks[-1].append((kind, g))


def holds(kind, g):
    """True, False, or None (undecided) for a condition on g."""
    g = sp.sympify(g)
    if kind == "intpow":                           # g = (base, integer exponent)
        b, k = g
        if k.is_nonnegative or b.is_nonzero:
            return True
        if k.is_negative and b.is_zero:
            return False
        return None
    if kind == "positive":
        r = g.is_positive
    elif kind == "nonneg":
        r = True if (g.is_nonnegative or g == 0) else (False if g.is_negative else None)
    elif kind == "nonzero":
        r = False if g.is_zero else g.is_nonzero
    else:                                          # 'unit': -1 <= g <= 1
        if g.is_real is False:
            return False
        lo, hi = sp.sympify(g + 1).is_nonnegative, sp.sympify(1 - g).is_nonnegative
        r = True if (lo and hi) else (False if (lo is False or hi is False) else None)
    if r is None and g.is_number:                  # a number SymPy left unevaluated: decide it
        try:
            c = complex(sp.N(g, 30))
        except (TypeError, ValueError):
            return None
        if abs(c.imag) > 1e-20:
            return False
        v = c.real
        r = {"positive": v > 0, "nonneg": v >= 0, "nonzero": v != 0, "unit": -1 <= v <= 1}[kind]
    return r


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
            if isinstance(n.op, ast.Div):
                _note(self.ctx, "nonzero", b)
            elif isinstance(n.op, ast.Pow):
                ob = _power_obligation(b, a)
                if ob:
                    _note(self.ctx, *ob)
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
            if n.func.id == "limit":
                # positional only, so that the written text of the expression and the point is
                # always seen (a keyword form would bypass the checks below)
                if n.keywords or len(n.args) != 3:
                    raise SceneError("limit(): write it as limit(expr, var, value), three arguments in that "
                                     "order, without keywords")
                # the limit's arguments are read into a list of their own: their conditions
                # (in the limit variable) are checked near the point by the limit, not by the
                # enclosing observe; the symbols written, and any arbitrary function, are found
                # part by part before SymPy's simplification can cancel them
                sinks = _sinks(self.ctx)
                sinks.append([])
                try:
                    args = [self.node(a) for a in n.args]
                    syms = self._limit_scan([n.args[0], n.args[2]])
                finally:
                    obligations = sinks.pop()
                return self.ctx.call("limit", args, {"_written": tuple(syms),
                                                     "_obligations": tuple(obligations)})
            args = [self.node(a) for a in n.args]
            kwargs = {k.arg: self.node(k.value) for k in n.keywords}
            out = self.ctx.call(n.func.id, args, kwargs)
            name = n.func.id
            if isinstance(out, sp.Basic) and not isinstance(out, sp.Tuple):
                for kind, g in _value_conditions(out):
                    _note(self.ctx, kind, g)
            if args and name not in getattr(self.ctx, "functions", {}) and isinstance(args[0], sp.Basic):
                a0 = sp.sympify(args[0])
                if name in ("log", "ln"):
                    _note(self.ctx, "positive", a0)
                elif name == "sqrt":
                    _note(self.ctx, "nonneg", a0)
                elif name in ("asin", "acos"):
                    _note(self.ctx, "unit", a0)
                elif name in ("tan", "sec"):
                    _note(self.ctx, "nonzero", sp.cos(a0))
                elif name in ("cot", "csc"):
                    _note(self.ctx, "nonzero", sp.sin(a0))
            return out
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

    def _limit_scan(self, nodes):
        """For limit(): the free symbols of every name written in the expression and the
        point, and of every call's value, found part by part (an observable such as y(p, ...)
        may hold symbols from its definition). A call to an arbitrary function (functions:),
        or a call whose value holds one, is refused: it is not a number. Unit names inside
        brackets are units, not names."""
        from sympy.core.function import AppliedUndef
        syms = set()
        funcs = getattr(self.ctx, "functions", {})

        def walk(x):
            if isinstance(x, ast.Subscript):           # value[unit]: the unit is parsed as a unit
                walk(x.value)
                return
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Name):
                name = x.func.id
                if name in funcs:
                    raise SceneError(f"limit(): {name} is an arbitrary function, not a number; apart from its "
                                     f"variable, everything in a limit must be a number")
                v = sp.sympify(self.val(x))
                if v.atoms(AppliedUndef):
                    raise SceneError(f"limit(): {name}(...) holds an arbitrary function, which is not a number; "
                                     f"apart from its variable, everything in a limit must be a number")
                syms.update(v.free_symbols)
                for a in list(x.args) + [k.value for k in x.keywords]:
                    walk(a)
                return
            if isinstance(x, ast.Name):
                try:
                    v = self.ctx.name(x.id)
                except SceneError:
                    return
                if isinstance(v, sp.Basic):
                    syms.update(v.free_symbols)
                return
            for child in ast.iter_child_nodes(x):
                walk(child)
        for nd in nodes:
            walk(nd)
        return syms

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


def written_obligations(text, ctx):
    """The conditions a written expression needs to be real and finite, recorded as it is
    read (before SymPy simplifies anything)."""
    translate(text, ctx, collect=True)
    return list(ctx.last_obligations)


def _power_obligation(k, base):
    """What base**k needs to be real and finite, or None: nothing for a nonnegative integer k;
    a nonzero base for any other integer k, numeric or symbolic ((-2)**n with n an integer is
    real); a nonnegative base for a positive non-integer k (0**(1/2) = 0); a positive base
    otherwise (a negative non-integer or a k that may not be an integer)."""
    k = sp.sympify(k)
    if k.is_integer:
        if k.is_nonnegative:
            return None
        if k.is_negative:
            return ("nonzero", base)
        # an integer exponent of unknown sign (an unknown n): decided once n is known,
        # 0**n is 0 for n = 2 and undefined for n = -1
        return ("intpow", sp.Tuple(base, k))
    if k.is_positive:
        return ("nonneg", base)
    return ("positive", base)


def _value_conditions(v):
    """The conditions a computed value needs to be real and finite, read from its SymPy tree
    (an observable's result such as sound_level(q) = 10 log10(q/I0) holds a log): a power's
    base (see _power_obligation), a log's argument positive, an asin/acos argument in
    [-1, 1], tan/sec cos != 0, cot/csc sin != 0."""
    out = []
    for node in sp.preorder_traversal(v):
        if isinstance(node, sp.Pow):
            ob = _power_obligation(node.exp, node.base)
            if ob:
                out.append(ob)
        elif isinstance(node, sp.log):
            out.append(("positive", node.args[0]))
        elif isinstance(node, (sp.asin, sp.acos)):
            out.append(("unit", node.args[0]))
        elif isinstance(node, (sp.tan, sp.sec)):
            out.append(("nonzero", sp.cos(node.args[0])))
        elif isinstance(node, (sp.cot, sp.csc)):
            out.append(("nonzero", sp.sin(node.args[0])))
    return out


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
