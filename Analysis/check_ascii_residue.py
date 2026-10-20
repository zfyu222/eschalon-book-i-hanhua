"""Re-check EXE ASCII candidates after stripping trailing data residue.

BlitzMax stores the string length elsewhere, so a byte-scan appends the next
field's characters to the text ("...for you?"E). Those variants never match the
corpus even though the clean sentence is translated. Trim to the last sentence
punctuation and compare again to expose real gaps only.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SOURCE = PROJECT / "eschalonbook_text.csv"
RAW = ROOT / "uncovered_exe_ascii.txt"

QUOTES = "\"'"
TAIL = re.compile(r"^(.*[.!?\"'\])])[\s\W]*$", re.S)


def norm(value):
    value = value.strip().strip(QUOTES).strip()
    return re.sub(r"\s+", " ", value)


def strip_residue(value):
    value = value.strip()
    match = TAIL.match(value)
    if match:
        value = match.group(1)
    return norm(value)


def covered(core, blob):
    """Accept a candidate when a long enough prefix appears in the corpus.

    Candidates carry trailing branch bytes, so exact equality is too strict.
    A 25+ character prefix match is specific enough to rule out coincidence.
    """
    for cut in (len(core), 80, 60, 40, 25):
        if cut > len(core):
            continue
        fragment = core[:cut]
        if len(fragment) >= 20 and fragment in blob:
            return True
    return False


def main():
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as stream:
        sources = [row[0] if row else "" for row in csv.reader(stream)]
    folded = {norm(s) for s in sources if s.strip()}
    blob = "\n".join(norm(s) for s in sources)

    lines = [l for l in RAW.read_text(encoding="utf-8").splitlines() if l.strip()]
    # Skip format strings, asset paths, config comments and identifiers.
    noise = re.compile(
        r"(?:[a-z]+::|[A-Za-z]:\\|\.(?:wav|ogg|png|pak|csv|ttf|bin|ent|map|exe|dll|ini|cfg|vdf|html?|bmp|jpg)\b"
        r"|^[;\[\]#]|^[/\\]|%[sdifx]|=)",
        re.IGNORECASE,
    )
    sentences = [l for l in lines if len(l.split()) >= 4 and not noise.search(l)]

    unresolved = []
    for value in sentences:
        core = strip_residue(value)
        if core in folded or covered(core, blob):
            continue
        unresolved.append(value)

    print(f"raw uncovered : {len(lines)}")
    print(f"sentence-like : {len(sentences)}")
    print(f"still missing : {len(unresolved)}")
    for value in unresolved[:40]:
        print("  ", repr(value[:120]))
    Path(ROOT / "uncovered_ascii_real.txt").write_text(
        "\n".join(unresolved), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
