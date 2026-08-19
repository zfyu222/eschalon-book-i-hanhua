"""Build a unified offline text corpus for Eschalon: Book I.

Sources:
1. Existing extracted/translated corpus.
2. BlitzMax UTF-16 String objects embedded in the executable.
3. Textual resources registered through the game's Incbin resource loader.
4. Runtime paragraph/display discovery logs (coverage validation).
5. Quoted user-facing literals in .ent entity scripts.

Outputs follow the workspace convention: one CSV record per text, one column.
"""
from __future__ import annotations

import csv
import json
import re
import struct
from collections import OrderedDict
from pathlib import Path

import pefile


ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "Eschalon_CN"
EXE = RUNTIME / "eschalon_book_1.exe"
SOURCE_CSV = ROOT / "eschalonbook_text.csv"
TRANSLATED_CSV = ROOT / "eschalonbook_text_translated.csv"
CATALOG_CSV = ROOT / "eschalonbook_text_catalog.csv"

BLITZ_STRING_TYPE = 0x4F1CB0
# Everything from this file offset onward belongs to the game rather than
# BlitzMax/DirectX runtime diagnostics. The first object is an Origin tooltip.
GAME_STRING_FILE_OFFSET = 0x1878F0
RESOURCE_REGISTER_TARGET = 0x465A81

FORMAT_MARKERS = "*&#^$"


def sanitize_extracted_text(text: str) -> str:
    """Remove binary record metadata without changing visible markup."""
    had_control = any(ord(char) < 32 and char not in "\r\n\t" for char in text)
    text = "".join(
        char for char in text
        if char in "\r\n\t" or ord(char) >= 32
    )
    # Entity records may append executable commands after the visible field.
    text = re.split(
        r"\n(?=(?:quest|remove_item|init_trade|screen_|map_|updatezones|areacheck)\b)",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    text = re.sub(
        r"\s*\|(?!\|)(?:quest|toggle|screen_[A-Za-z_]*|map_[A-Za-z_]*|"
        r"remove_[A-Za-z_]*|init_[A-Za-z_]*|updatezones|areacheck)\b.*$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = text.strip("\x00\r\n\t ")
    if had_control:
        # A one-byte choice/branch id often sits after the final quote or
        # bracket and immediately before the binary control byte.
        anchors = [text.rfind('"'), text.rfind("]"), text.rfind("."), text.rfind("!"), text.rfind("?")]
        anchor = max(anchors)
        if anchor >= 0 and len(text) - anchor - 1 <= 2:
            text = text[:anchor + 1]
    text = text.strip("\x00\r\n\t ")
    # The translation pipeline requires one physical CSV line per text. Store
    # embedded line breaks as the two literal characters "\n"; the runtime
    # loader restores them after reading the aligned CSV records.
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")


def read_first_column(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    if rows and rows[0] and rows[0][0].strip() in {"原文", "译文"}:
        rows = rows[1:]
    return [row[0] for row in rows if row]


def load_existing_mapping() -> dict[str, str]:
    original_path = ROOT / "translated_strings.csv"
    translated_path = ROOT / "translated_strings_translated.csv"
    originals = read_first_column(original_path)
    translations = read_first_column(translated_path)
    mapping: dict[str, str] = {}
    for source, target in zip(originals, translations):
        source = sanitize_extracted_text(source)
        target = sanitize_extracted_text(target)
        if source and target and source != target and "\ufffd" not in target:
            mapping[source] = target

    # The legacy pair contains multiline prose with inconsistent embedded quote
    # escaping. Its physical lines are still exactly aligned, so recover every
    # independently balanced one-line entry (notably item/UI names) this way.
    source_lines = original_path.read_text(encoding="utf-8-sig").splitlines()
    target_lines = translated_path.read_text(encoding="utf-8-sig").splitlines()
    for source_line, target_line in zip(source_lines[1:], target_lines[1:]):
        if source_line.count('"') % 2 or target_line.count('"') % 2:
            continue
        try:
            source_row = next(csv.reader([source_line]))
            target_row = next(csv.reader([target_line]))
        except (csv.Error, StopIteration):
            continue
        if not source_row or not target_row:
            continue
        source = sanitize_extracted_text(source_row[0])
        target = sanitize_extracted_text(target_row[0])
        if source and target and source != target and "\ufffd" not in target:
            mapping[source] = target
    return mapping


def is_readable(text: str) -> bool:
    return bool(text) and all(
        char in "\r\n\t" or ord(char) >= 32
        for char in text
    )


def looks_translatable(text: str) -> bool:
    text = text.strip("\x00\r\n\t ")
    if len(text) < 2 or not re.search(r"[A-Za-z]", text):
        return False
    if "\ufffd" in text:
        return False
    lower = text.lower()
    if lower.startswith("incbin/"):
        return False
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.(?:wav|ogg|png|jpg|ttf|ent|map|tre|csv)", text):
        return False
    if re.fullmatch(r"(?:0x)?[0-9a-fA-F]{6,}", text):
        return False
    return True


def strip_format_for_key(text: str) -> str:
    # Do not remove markers in the actual corpus; this helper is only used to
    # reject strings consisting solely of formatting/control symbols.
    return text.strip(FORMAT_MARKERS + " \r\n\t")


def extract_blitz_strings(exe_data: bytes) -> list[tuple[str, str]]:
    signature = struct.pack("<I", BLITZ_STRING_TYPE)
    results: list[tuple[str, str]] = []
    cursor = GAME_STRING_FILE_OFFSET
    while True:
        offset = exe_data.find(signature, cursor)
        if offset < 0:
            break
        cursor = offset + 4
        if offset + 12 > len(exe_data):
            continue
        length = struct.unpack_from("<I", exe_data, offset + 8)[0]
        end = offset + 12 + length * 2
        if not 0 < length <= 20000 or end > len(exe_data):
            continue
        try:
            text = exe_data[offset + 12:end].decode("utf-16le")
        except UnicodeDecodeError:
            continue
        if is_readable(text) and looks_translatable(text) and strip_format_for_key(text):
            results.append((text, f"exe:blitz_string@0x{offset:X}"))
    return results


def va_bytes(pe: pefile.PE, exe_data: bytes, va: int, size: int) -> bytes:
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    offset = pe.get_offset_from_rva(rva)
    return exe_data[offset:offset + size]


def find_registered_resources(pe: pefile.PE, exe_data: bytes) -> list[tuple[int, bytes]]:
    """Find all 52 generated `Incbin` registration sequences statically."""
    blocks: list[tuple[int, bytes]] = []
    for section in pe.sections:
        section_data = section.get_data()
        section_va = pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress
        for index in range(0, max(0, len(section_data) - 29)):
            if section_data[index] != 0xB8 or section_data[index + 5] != 0x2D:
                continue
            if section_data[index + 10] != 0x50:
                continue
            if section_data[index + 11] != 0x68 or section_data[index + 16] != 0x68:
                continue
            if section_data[index + 21] != 0xE8:
                continue
            if section_data[index + 26:index + 29] != b"\x83\xC4\x0C":
                continue
            call_va = section_va + index + 21
            relative = struct.unpack_from("<i", section_data, index + 22)[0]
            if call_va + 5 + relative != RESOURCE_REGISTER_TARGET:
                continue
            data_end = struct.unpack_from("<I", section_data, index + 1)[0]
            sub_start = struct.unpack_from("<I", section_data, index + 6)[0]
            push_start = struct.unpack_from("<I", section_data, index + 12)[0]
            if sub_start != push_start:
                continue
            size = data_end - push_start
            if not 0 < size <= 2_000_000:
                continue
            try:
                payload = va_bytes(pe, exe_data, push_start, size)
            except Exception:
                continue
            blocks.append((push_start, payload))
    return blocks


def add_literal(results: list[tuple[str, str]], text: str, source: str) -> None:
    text = text.strip("\x00\r\n\t ")
    if looks_translatable(text) and strip_format_for_key(text):
        results.append((text, source))


def extract_resource_literals(blocks: list[tuple[int, bytes]]) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for va, payload in blocks:
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            continue
        printable = sum(char in "\r\n\t" or ord(char) >= 32 for char in text)
        if not text or printable / len(text) < 0.98:
            continue
        source = f"exe:resource@0x{va:X}"

        # CSV resources contain item names, entity labels, spell names, etc.
        lines = text.splitlines()
        csv_like = (
            len(lines) > 5
            and text.count(",") >= len(lines) * 2
            and text.count('"') >= len(lines) * 2
        )
        if csv_like:
            for line in lines:
                try:
                    row = next(csv.reader([line]))
                except (csv.Error, StopIteration):
                    continue
                for field in row:
                    add_literal(results, field, source + ":csv")

        # Script/narrative resources: collect quoted literals and explicit
        # Message(...) arguments without translating whole command programs.
        for match in re.finditer(
            r"""(?is)\b(?:message|say|caption|title)\s*\(\s*["'](.*?)["']\s*\)""",
            text,
        ):
            add_literal(results, match.group(1), source + ":call")
        # Books and some narrative tables store prose as unquoted records.
        for line in lines:
            candidate = line.strip()
            if "|" in candidate:
                candidate = candidate.split("|", 1)[0].rstrip()
            if len(candidate) >= 20 and (
                " " in candidate
                and re.search(r"[.!?]", candidate)
                and not re.match(r"^[A-Za-z_]+\s*\(", candidate)
            ):
                add_literal(results, candidate, source + ":line")
    return results


def extract_entity_literals() -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    data_dir = RUNTIME / "data"
    for path in sorted(data_dir.glob("*.ent")):
        text = path.read_bytes().decode("utf-8", errors="ignore")
        for match in re.finditer(
            r"""(?is)\b(?:message|say|caption|title)\s*\(\s*["'](.*?)["']\s*\)""",
            text,
        ):
            add_literal(results, match.group(1), f"data:{path.name}:call")
        for match in re.finditer(r'"([^"\r\n]{3,})"', text):
            add_literal(results, match.group(1), f"data:{path.name}:quoted")
    return results


def extract_runtime_log(path: Path, kind: str) -> list[tuple[str, str]]:
    if not path.exists():
        return []
    results: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            text = json.loads(line).get("text", "")
        except json.JSONDecodeError:
            continue
        # Drop per-word artifacts produced by the final Draw hook. Retain
        # multi-word labels and standalone title-like UI labels only.
        if kind == "runtime_draw":
            if text != text.strip():
                continue
            if " " not in text and not re.fullmatch(r"[A-Z][A-Za-z0-9'-]*|[A-Z0-9_-]+", text):
                continue
        add_literal(results, text, kind)
    return results


def write_one_column(path: Path, values: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        for value in values:
            writer.writerow([value])


def main() -> int:
    if not EXE.exists():
        raise SystemExit(f"Missing executable: {EXE}")

    exe_data = EXE.read_bytes()
    pe = pefile.PE(data=exe_data, fast_load=True)
    # The unified corpus is a clean translation pass. Do not inherit the
    # project's earlier experimental translations.
    existing_mapping: dict[str, str] = {}

    entries: OrderedDict[str, dict[str, object]] = OrderedDict()

    def merge(text: str, source: str) -> None:
        text = sanitize_extracted_text(text)
        if not is_readable(text) or not looks_translatable(text):
            return
        record = entries.setdefault(text, {"sources": [], "translation": ""})
        sources = record["sources"]
        if isinstance(sources, list) and source not in sources:
            sources.append(source)
        # Legacy multiline translations lost/shifted embedded line breaks in
        # places. Keep those rows pending rather than inheriting unsafe text.
        if not record["translation"] and "\\n" not in text and text in existing_mapping:
            record["translation"] = existing_mapping[text]

    # Preserve the established order first so existing translations remain
    # stable, then append newly discovered offline strings.
    for text in read_first_column(ROOT / "translated_strings.csv"):
        merge(text, "existing_corpus")

    static_strings = extract_blitz_strings(exe_data)
    for text, source in static_strings:
        merge(text, source)

    blocks = find_registered_resources(pe, exe_data)
    resource_literals = extract_resource_literals(blocks)
    for text, source in resource_literals:
        merge(text, source)

    entity_literals = extract_entity_literals()
    for text, source in entity_literals:
        merge(text, source)

    for log_name, kind in (
        ("runtime_paragraphs.jsonl", "runtime_paragraph"),
        ("runtime_untranslated.jsonl", "runtime_draw"),
    ):
        for text, source in extract_runtime_log(ROOT / log_name, kind):
            merge(text, source)

    originals = list(entries)
    # The template deliberately retains English for untranslated rows. This
    # keeps strict one-to-one alignment and is immediately safe to load.
    translations = [
        str(entries[text]["translation"] or text)
        for text in originals
    ]
    write_one_column(SOURCE_CSV, originals)
    write_one_column(TRANSLATED_CSV, translations)

    with CATALOG_CSV.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["原文", "当前译文", "状态", "来源"])
        for source, target in zip(originals, translations):
            writer.writerow([
                source,
                target,
                "translated" if target != source else "pending",
                " | ".join(entries[source]["sources"]),
            ])

    translated_count = sum(source != target for source, target in zip(originals, translations))
    print(f"Registered resources found: {len(blocks)}")
    print(f"BlitzMax game strings: {len(static_strings)}")
    print(f"Resource literals: {len(resource_literals)}")
    print(f"Entity literals: {len(entity_literals)}")
    print(f"Unified unique texts: {len(originals)}")
    print(f"Existing translations reused: {translated_count}")
    print(f"Pending translation: {len(originals) - translated_count}")
    print(f"Source: {SOURCE_CSV}")
    print(f"Translation template: {TRANSLATED_CSV}")
    print(f"Catalog: {CATALOG_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
