"""Attribute each runtime unmatched string to its root cause.

For every fragment the hook failed to translate, decide whether
  ABSENT  the corpus has no matching entry at all, or
  BLOCKED the corpus has the sentence but the lookup chain cannot reach it,
and report which index threshold blocked it.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import display_hook_launcher as hook  # noqa: E402

LOG = ROOT / "runtime_untranslated.jsonl"

WORD_RE = re.compile(r"[A-Za-z][A-Za-z']{5,}")
QUOTE_EDGE = re.compile(r'^[\s"\'\[\]]+|[\s"\'\[\]]+$')


def norm(value):
    value = re.sub(r"[\u0019\u2018\u2019]", "'", value)
    value = re.sub(r"[\u001c\u201d\u201c]", '"', value)
    return re.sub(r"\s+", " ", value).strip()


def bare_of(value):
    return QUOTE_EDGE.sub("", value).strip()


def main():
    mapping, _offline, _overrides = hook.load_offline_mapping()
    word_index = hook._build_word_index(mapping)
    prefix_index = hook._build_prefix_index(mapping)
    corpus_norm = {norm(k): k for k in mapping}

    entries = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line)["text"])
        except (json.JSONDecodeError, KeyError):
            continue

    absent, blocked, ok = [], [], []
    for text in entries:
        key = norm(text)
        if key in corpus_norm:
            ok.append((text, "exact-after-norm"))
            continue

        bare = bare_of(key)
        fragment_key = corpus_norm.get(bare)
        if fragment_key is not None:
            ok.append((text, "bare-exact"))
            continue

        # Does any corpus entry contain this fragment?
        owner = None
        for candidate, original in corpus_norm.items():
            if len(bare) >= 12 and bare in candidate:
                owner = original
                break

        if owner is not None:
            # Entry exists; why did the runtime miss it?
            indexed = len(owner) >= 40
            blocked.append((text, owner, indexed))
            continue

        # No exact containment: try word-index reachability.
        words = sorted({w.lower() for w in WORD_RE.findall(bare)}, key=len, reverse=True)[:5]
        reachable = [w for w in words if w in word_index]
        if reachable:
            blocked.append((text, f"wordIndex:{reachable[:2]}", True))
        else:
            absent.append(text)

    print(f"total unmatched: {len(entries)}")
    print(f"  recoverable by lookup : {len(ok)}")
    print(f"  blocked by matching   : {len(blocked)}")
    print(f"  absent from corpus    : {len(absent)}")

    print("\n-- blocked (entry exists, lookup missed) --")
    for text, owner, indexed in blocked:
        tag = "indexed" if indexed else "SHORT<40"
        print(f"  [{tag}] {text[:60]!r}")
        print(f"           owner={str(owner)[:70]!r}")

    print("\n-- absent (needs new translation) --")
    for text in absent:
        print(f"  {text[:80]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
