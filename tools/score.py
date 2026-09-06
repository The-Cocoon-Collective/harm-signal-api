#!/usr/bin/env python3
"""
Score signals against a synthetic run's answer key.

    python3 tools/score.py signals.ndjson synthetic.ndjson.answers.json

Reports, per planted shape: found or missed, and at what confidence. Then everything else
raised, which is your false-positive count.

False positives are not a footnote here. Every one of them is a real person being flagged
to another person for something they did not do. An analyzer that catches everything by
raising everything has not solved the problem, it has moved it onto whoever reads the
output. Report both numbers or neither.
"""
import argparse, json, sys

def load(p):
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("signals")
    ap.add_argument("answers")
    a = ap.parse_args()

    signals = load(a.signals)
    planted = json.load(open(a.answers, encoding="utf-8"))["planted"]

    want = {
        "isolation":            planted["isolation"],
        "asymmetric_attention": planted["asymmetric_attention"]["actor"],
        "withdrawal":           planted["withdrawal"],
        "novel_contact":        planted["novel_contact"],
    }

    hits, used = {}, set()
    for cls, ref in want.items():
        for i, s in enumerate(signals):
            if s["class"] == cls and s["subject"]["ref"] == ref:
                hits[cls] = s
                used.add(i)
                break

    print(f"{len(signals)} signal(s) raised, {len(want)} shape(s) planted\n")
    for cls, ref in want.items():
        s = hits.get(cls)
        if s:
            print(f"  FOUND   {cls:<22} conf {s['confidence']:<5} {s['rationale']}")
        else:
            print(f"  MISSED  {cls:<22} {ref[:16]}...")

    extra = [s for i, s in enumerate(signals) if i not in used]
    print(f"\n  {len(extra)} signal(s) not in the answer key "
          f"-- false positives, or something the generator did not intend to plant:")
    for s in extra:
        print(f"    {s['class']:<22} {s['subject']['ref'][:16]}...  conf {s['confidence']}")

    print(f"\nrecall {len(hits)}/{len(want)}   raised {len(signals)}   "
          f"unexplained {len(extra)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
