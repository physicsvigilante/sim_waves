"""Usage: python3 dedupe.py "<statement text>"  -> top 3 most similar corpus statements (id, score).
Run from the project root. A score above about 0.75 with the same numbers suggests a duplicate."""
import difflib, glob, sys, yaml
q = " ".join(sys.argv[1].lower().split())
scores = []
for f in glob.glob("corpus/[0-9]*/**/*.yaml", recursive=True):
    try:
        d = yaml.safe_load(open(f))
    except Exception:
        continue
    if not isinstance(d, dict) or "statement" not in d:
        continue
    s = " ".join(str(d["statement"]).lower().split())
    scores.append((difflib.SequenceMatcher(None, q, s).ratio(), d.get("id")))
for sc, i in sorted(scores, reverse=True)[:3]:
    print(f"{sc:.2f} {i}")
