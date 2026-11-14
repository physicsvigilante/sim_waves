"""Usage:
  python -m simwaves run  <scene.yaml>               evaluate one scene
  python -m simwaves test <folder>                   run every scene's expect block
  python -m simwaves view <out.html> <scene.yaml>... build a viewer page from scenes
"""
import sys

from .errors import SceneError
from .harness import run_dir
from .run import evaluate, load, show


def _round(o):
    if isinstance(o, float):
        return float(f"{o:.5g}")
    if isinstance(o, list):
        return [_round(v) for v in o]
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    return o


def view(out, files):
    import json
    import os
    import yaml
    from .export import export
    from .run import _Loader
    from .errors import SceneError as _SE
    data = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            data.append(_round(export(yaml.load(fh, Loader=_Loader))))
    tpl = open(os.path.join(os.path.dirname(__file__), "..", "viewer", "template.html"), encoding="utf-8").read()
    # allow_nan=False: a NaN would make the page's JSON unparseable; '<' is escaped so
    # scene text can never close the data block or open an HTML comment inside it.
    blob = json.dumps(data, allow_nan=False).replace("<", "\\u003c")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(tpl.replace("/*DATA*/", blob))
    print(f"wrote {out} ({len(data)} scenes)")
    return 0


def main(argv):
    if len(argv) >= 3 and argv[0] == "view":
        try:
            return view(argv[1], argv[2:])
        except SceneError as exc:
            print(f"{type(exc).__name__}: {exc}")
            return 1
    if len(argv) != 2 or argv[0] not in ("run", "test"):
        print(__doc__)
        return 2
    if argv[0] == "test":
        counts = run_dir(argv[1])
        return 0 if set(counts) <= {"PASS"} else 1
    try:
        sol, res = evaluate(load(argv[1]))
    except SceneError as exc:
        sol_, res_ = getattr(exc, "partial", ({}, {}))
        for k, v in list(sol_.items()) + list(res_.items()):
            print(f"{k} = {show(v)}")
        print(f"{type(exc).__name__}: {exc}")
        return 1
    for k, v in sol.items():
        print(f"solved {k} = {show(v)}")
    for k, v in res.items():
        print(f"{k} = {show(v)}")
    return 0


sys.exit(main(sys.argv[1:]))
