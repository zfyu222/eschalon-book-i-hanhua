"""Reproduce the JS dialogue lookup in Python for the Father Michael panel.

The screenshot mixes Chinese and English inside one panel, so the hook clearly
reaches it. This replays DRAW_TEXT's fallback chain line by line to find which
step fails for each visible line.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import display_hook_launcher as hook  # noqa: E402

# Wrapped lines as the engine hands them to draw, taken from the screenshot.
LINES = [
    "Standing in this small church is a fair man of",
    "slight build, bathed in colored light streaming",
    "through the stained glass windows. Incense wafts",
    "through the air creating a pleasant, hazy aura.",
    '"Welcome to the Bethel of the Green Moon, weary',
    "traveler! My name is Father Michael. Here at the",
    "Bethel we can heal your wounds and restore your",
    'soul, for a small donation of course."',
    '"I am in need of healing."',
    '"I was hoping the Bethel would have some work for',
    'me."',
    '"I am cursed and need spiritual restoration."',
]

WORD_RE = re.compile(r"[A-Za-z][A-Za-z']{5,}")
QUOTE_EDGE = re.compile(r'^[\s"\'\[\]]+|[\s"\'\[\]]+$')


def norm(value):
    value = re.sub(r"[\u0019\u2018\u2019]", "'", value)
    value = re.sub(r"[\u001c\u001d\u201c\u201d]", '"', value)
    value = re.sub(r"[\u0000-\u0008\u000b\u000c\u000e-\u0018\u001a-\u001f]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def strip_record_quotes(value):
    return QUOTE_EDGE.sub("", value).strip()


def main():
    mapping, _offline, _overrides = hook.load_offline_mapping()
    word_index = hook._build_word_index(mapping)
    prefix_index = hook._build_prefix_index(mapping)

    print(f"mapping={len(mapping)} wordIndexKeys={len(word_index)} prefixKeys={len(prefix_index)}")

    for line in LINES:
        source = norm(line)
        stage = "exact"
        target = mapping.get(source)
        if target is None:
            stage = "exact-trim"
            target = mapping.get(source.strip())
        if target is None:
            stage = "fragment"
            bare = strip_record_quotes(source)
            words = sorted({w.lower() for w in WORD_RE.findall(bare)}, key=len, reverse=True)[:5]
            for word in words:
                for candidate in word_index.get(word, []):
                    norm_source = norm(candidate)
                    if bare in norm_source:
                        target = mapping.get(candidate)
                        stage = f"fragment[{word}]"
                        break
                if target:
                    break
        if target is None:
            stage = "prefix"
            token = " ".join(source.split(" ")[:2])
            for candidate in prefix_index.get(token, []):
                if norm(candidate).startswith(source):
                    target = mapping.get(candidate)
                    stage = f"prefix[{token}]"
                    break

        status = "HIT " if target else "MISS"
        detail = f"stage={stage}"
        if target:
            detail += f" key={target[:28]!r}"
        print(f"{status} {line[:58]!r}")
        print(f"      {detail}")

    # Why the short option is not indexed.
    short = "I am in need of healing."
    print(f"\nlen({short!r}) = {len(short)}  (index requires >= 40)")
    print(f"  in wordIndex 'healing'? {'healing' in word_index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
