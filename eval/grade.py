"""Grade an authoring run: compare work/<id>.answer.yaml with the corpus book keys.

usage: python3 eval/grade.py eval/run1
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "corpus")


def key_for(pid):
    folder, sub, name = pid.split("/")
    if folder == "B4":
        f = os.path.join(CORPUS, "book4_waves", sub, f"{name}.yaml")
        return yaml.safe_load(open(f)) if os.path.exists(f) else None
    hits = glob.glob(os.path.join(CORPUS, f"{folder}_*", f"{sub}_*", f"{name}.yaml"))
    return yaml.safe_load(open(hits[0])) if hits else None


def num(v):
    m = re.search(r"-?\d+(\.\d+)?(e-?\d+)?", str(v))
    return float(m.group(0)) if m else None


def match(rec, ans):
    fmt, key = rec["format"], rec.get("answer")
    if fmt in ("single_correct", "multiple_correct"):
        if isinstance(ans, str):           # e.g. "c (880 Hz)" or "b, d"
            head = re.split(r"[(\[]", ans.replace("[", "").replace("]", ""), maxsplit=1)[0] \
                if not ans.strip().startswith("[") else ans
            got = re.findall(r"\b([a-d])\b", head.lower())
        else:
            got = ans if isinstance(ans, list) else [ans]
        if isinstance(key, str):
            key = re.findall(r"\b([a-dA-D])\b", key)
        key = key if isinstance(key, list) else [key]
        return sorted(str(a).strip("() ").lower() for a in got) == sorted(str(k).strip().lower() for k in key)
    if fmt == "numerical":
        want = rec["answer_value"]
        if isinstance(want, dict):
            if not isinstance(ans, dict):
                return False
            return all(abs((num(ans.get(k)) or 1e99) - float(v)) <= 0.02 * max(1, abs(float(v)))
                       for k, v in want.items())
        g = num(ans)
        return g is not None and abs(abs(g) - abs(float(want))) <= 0.02 * max(1.0, abs(float(want)))
    if fmt == "matrix_match":
        if isinstance(key, str):
            key = {k.lower(): [x.strip().lower() for x in re.split(r"[,\s]+", v) if x.strip()]
                   for k, v in re.findall(r"([A-Da-d])\s*(?:->|→|:|-)\s*([p-tP-T](?:\s*,\s*[p-tP-T])*)", key)}
        if isinstance(ans, str):           # "a->s, b->r"
            ans = {k: v for k, v in re.findall(r"([a-d])\s*(?:->|→|:)\s*([p-t])", ans)}
        if not isinstance(ans, dict):
            return False
        norm = lambda v: sorted(v) if isinstance(v, list) else [v]
        return all(norm(ans.get(k)) == norm(v) for k, v in key.items())
    return False


def main(run):
    rows, n_ok, n_first = [], 0, 0
    for f in sorted(glob.glob(os.path.join(run, "work", "*.answer.yaml"))):
        pid_file = os.path.basename(f).replace(".answer.yaml", "")
        prob = yaml.safe_load(open(os.path.join(run, "problems", pid_file + ".yaml")))
        rec = key_for(prob["id"])
        try:
            a = yaml.safe_load(open(f)) or {}
        except yaml.YAMLError:
            m = re.search(r"^answer:\s*(.*)$", open(f).read(), re.M)
            raw = m.group(1) if m else ""
            try:
                val = yaml.safe_load(raw)
            except yaml.YAMLError:
                lead = re.match(r"\s*(\[[^\]]*\])", raw)
                val = yaml.safe_load(lead.group(1)) if lead else raw
            fit = re.search(r"^engine_fit:\s*(\S+)", open(f).read(), re.M)
            a = {"answer": val, "engine_fit": (fit.group(1) if fit else "?") + "(bad yaml)"}
        attempts = len(glob.glob(os.path.join(run, "work", pid_file + ".v*.yaml")))
        try:
            ok = match(rec, a.get("answer"))
        except (ValueError, TypeError, AttributeError):
            ok = None                      # needs a human or agent grader (symbolic / multi-part)
        n_ok += bool(ok)
        n_first += bool(ok) and attempts == 1
        n_manual = locals().get("n_manual", 0) + (ok is None)
        rows.append((prob["id"], attempts, a.get("engine_fit"), ok, a.get("answer"),
                     rec.get("answer", rec.get("answer_value"))))
    print(f"{'id':16} att fit      ok   answer -> key")
    for r in rows:
        print(f"{r[0]:16} {r[1]:3} {str(r[2]):8} {'?' if r[3] is None else ('Y' if r[3] else 'n'):4} {r[4]} -> {r[5]}")
    print(f"\ncorrect {n_ok}/{len(rows)}; correct on first attempt {n_first}/{len(rows)}")


main(sys.argv[1])
