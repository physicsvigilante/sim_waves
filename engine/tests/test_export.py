"""Regression checks for the view/verification review findings.  Run from engine/:
    python3 tests/test_export.py
"""
import copy
import json
import os
import sys

import sympy as sp
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from simwaves.errors import SceneError                      # noqa: E402
from simwaves.export import ViewError, export              # noqa: E402
from simwaves.run import _Loader, load                     # noqa: E402
from simwaves.scene import Scene, equivalent               # noqa: E402
from simwaves.solver import _relations, _verify, solve_given  # noqa: E402

BASE = {
    "symbols": {"a": "positive"},
    "waves": {"w": {"harmonic": {"A": "a", "f": "5 Hz", "v": "2 m/s", "dir": "+x", "phase": 0}}},
    "observe": {"amp": "amplitude(w)"},
    "illustrate": {"a": "1 cm"},
    "view": [{"snapshot": "w", "t": "0 s"}],
}
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def raises(fn, kind=SceneError):
    try:
        fn()
    except kind as exc:
        return str(exc)
    return None


def scene(**over):
    d = copy.deepcopy(BASE)
    d.update(over)
    return d


# 1. a rejected varied value carries no results of its own
d = scene(explore={"vary": {"waves.w.harmonic.v": ["2 m/s", "0 m/s"]}})
out = export(d)
bad = out["variants"]["items"][1]
check("1 rejected value has error and no results", "error" in bad and "results" not in bad, bad.get("error", ""))
# 4. ...and nothing non-finite reaches the JSON
json.dumps(out, allow_nan=False)
check("4 export is NaN-free JSON", True)

# 2. provenance follows the varied value; source value marked
d = scene(explore={"vary": {"a": ["1 cm", "2 cm"]}})
out = export(d)
it = out["variants"]["items"]
check("2 illustrative follows variant", it[1]["illustrative"]["a"] == "2 cm" and it[0]["illustrative"]["a"] == "1 cm")
check("2 source value marked", it[0]["is_source"] and not it[1]["is_source"])
check("2 target kind reported", out["variants"]["target_kind"] == "illustrative value")
check("2 per-variant verification/facts exported", all("verification" in x and "facts" in x for x in it))

# 3. illustrate is checked for dimension, kind and unit
check("3 wrong dimension rejected", raises(lambda: export(scene(illustrate={"a": "3 s"})), ViewError))
check("3 negative value for positive symbol rejected", raises(lambda: export(scene(illustrate={"a": "-5 cm"})), ViewError))
check("3 bare number without unit rejected", raises(lambda: export(scene(illustrate={"a": "3"})), ViewError))
check("3 x window with time unit rejected",
      raises(lambda: export(scene(view=[{"snapshot": "w", "t": "0 s", "x": ["0 s", "1 s"]}])), ViewError))
check("4 zero or negative speed rejected", raises(lambda: Scene(scene(waves={"w": {"harmonic": {
    "A": "1 cm", "f": "5 Hz", "v": "-3 m/s", "dir": "+x", "phase": 0}}}))))

# 5. plot ranges stay fixed across varied values (they used to rescale with the period)
d = yaml.load(open("../eval/view_exp/scenes/05_bmc_004.yaml"), Loader=_Loader)
out = export(d)
ranges = {(p["v"][0], p["v"][-1]) for x in out["variants"]["items"] for p in x["panels"] if p and p["kind"] == "plot"}
check("5 plot range identical across variants", len(ranges) == 1, str(ranges))
yr = {tuple(p["y_range"]) for x in out["variants"]["items"] for p in x["panels"] if p and p["kind"] == "animate"}
check("S1 animation y-range fixed across frames and variants", len(yr) == 1, str(yr))

# 6. each panel keeps its own author window inside variants
d = scene(view=[{"snapshot": "w", "t": "0 s", "x": ["0 m", "1 m"]},
                {"snapshot": "w", "t": "0 s", "x": ["0 m", "10 m"]}],
          explore={"vary": {"a": ["1 cm", "2 cm"]}})
out = export(d)
ends = [(p["x"][-1]) for p in out["variants"]["items"][1]["panels"]]
check("6 per-panel windows preserved in variants", ends == [1.0, 10.0], str(ends))

# 7. _verify rejects a value that satisfies the facts but violates its declared kind
sc = Scene({"symbols": {"a": "positive"}, "unknowns": {"u": "positive"}, "given": ["u**2 == 4*a**2"]})
sol = solve_given(sc)
u = [k for k in sol][0]
msg = raises(lambda: _verify(sc, _relations(sc), {u: -2 * sc.names["a"]}))
check("7 _verify checks declared kinds", msg and "declared kind" in msg, msg or "")

# 8. a true redundant fact is not a contradiction
sc = Scene({"symbols": {"a": "positive"}, "unknowns": {"u": "real"},
            "given": ["u == a", "sin(a)**2 + cos(a)**2 == 1"]})
check("8 redundant identity accepted", solve_given(sc)[sc.names["u"]] == sc.names["a"])

# 9. plot axis label states the SI unit actually plotted
d = {"symbols": {"L": "positive"}, "media": {"s": {"type": "string", "mu": "0.1 kg/m", "tension": "10 N"}},
     "waves": {"w": {"harmonic": {"on": "s", "A": "1 cm", "f": "5 Hz", "dir": "+x", "phase": 0}}},
     "view": [{"plot": "y(w, x=L, t=0)", "vs": "L", "range": ["10 cm", "50 cm"]}]}
p = export(d)["panels"][0]
check("9 plot x label is SI", p["x_label"] == "L (m)" and abs(p["v"][0] - 0.1) < 1e-12, p["x_label"])

# 10. malformed view/explore are rejected cleanly
check("10 unknown panel key rejected",
      raises(lambda: export(scene(view=[{"snapshot": "w", "t": "0 s", "bogus_key": 3}])), ViewError))
check("10 malformed explore rejected", raises(lambda: export(scene(explore={"vary": "a"}))))

# 11. no spurious 'missing' entries in variants
d = scene(explore={"vary": {"a": ["1 cm", "2 cm"]}})
check("11 variants carry no spurious missing", all(not x["missing"] for x in export(d)["variants"]["items"]))

# 12. equivalent(): near-identities are not 'sampled' as equal
a = sp.Symbol("a", positive=True)
truth, basis = equivalent(sp.sin(a) ** 2 + sp.cos(a) ** 2 - 1 + sp.exp(-1000 * a), sp.Integer(0))
check("12 tiny-but-nonzero difference detected", truth is False, basis)

# S2. scene text cannot break out of the data block
d = scene(assume=["<!--<script>alert(1)</script>"])
import subprocess, tempfile  # noqa: E401
with tempfile.TemporaryDirectory() as td:
    f = os.path.join(td, "s.yaml")
    yaml.safe_dump(d, open(f, "w"))
    out_html = os.path.join(td, "v.html")
    subprocess.run([sys.executable, "-m", "simwaves", "view", out_html, f], check=True, capture_output=True)
    html = open(out_html).read()
    blob = html.split('type="application/json">', 1)[1].split("</script>", 1)[0]
    check("S2 data block contains no raw '<'", "<" not in blob)

# 10: list-valued and unavailable observables are exported, not crashes (diag1 teacher test)
lst = export({"media": {"air": {"type": "gas", "v": "340 m/s"}},
              "resonators": {"p": {"type": "pipe", "on": "air", "length": "85 cm", "ends": ["closed", "open"],
                                   "end_correction": "0 m"}},
              "observe": {"nodes": "nodes(p, harmonic=3)", "bad": "frequency(p, harmonic=2)"},
              "view": [{"plot": "frequency(p, harmonic=1)*s", "vs": "s", "range": ["0 m", "1 m"]}],
              "symbols": {"s": "positive"}})
r10 = lst["results"]
check("10 list observable exported as text", r10["nodes"]["value"] is None and "17/30" in r10["nodes"]["text"],
      str(r10.get("nodes")))
check("10 unavailable observable marked, others kept", r10["bad"].get("unavailable") is True, str(r10.get("bad")))

bad = [r for r in results if not r[1]]
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
print(f"\nsummary: {len(results) - len(bad)}/{len(results)} passed")
sys.exit(1 if bad else 0)
