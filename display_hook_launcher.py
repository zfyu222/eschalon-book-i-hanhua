"""Eschalon Book I Chinese launcher using a display-layer text hook.

The game uses item names as both visible labels and internal identifiers.
Changing the embedded item table therefore breaks map/container lookups.
This launcher leaves all game data untouched and replaces only the BlitzMax
String passed to brl.max2d.TImageFont.Draw (VA 0x477B47).
"""
import csv
import json
import os
import re
import sys
from pathlib import Path

import frida

import launch_chinese as base


core = base.core
DRAW_TEXT_VA = 0x477B47
MESSAGE_PREWRAP_VA = 0x4BDEB8
POPUP_PREWRAP_VA = 0x4C4982
SKILL_PARAGRAPH_VA = 0x4D950F
NARRATIVE_PREWRAP_VA = 0x4C6C53  # branch merge point in FUN_004c69ad, before wrapping
BLITZ_STRING_TYPE = 0x4F1CB0
UNTRANSLATED_LOG = Path(__file__).resolve().parent / "runtime_untranslated.jsonl"
CALLSTACK_LOG = Path(__file__).resolve().parent / "runtime_callstacks.jsonl"
PARAGRAPH_LOG = Path(__file__).resolve().parent / "runtime_paragraphs.jsonl"
NARRATIVE_CALL_LOG = Path(__file__).resolve().parent / "runtime_narrative_calls.jsonl"
OFFLINE_SOURCE = Path(__file__).resolve().parent / "eschalonbook_text.csv"
OFFLINE_TRANSLATED = Path(__file__).resolve().parent / "eschalonbook_text_translated.csv"
RUNTIME_OVERRIDES = Path(__file__).resolve().parent / "runtime_fragment_overrides.json"
SCREEN_CFG = Path.home() / "Documents" / "Eschalon Book 1 Saved Games" / "eschalon.cfg"


def ensure_fullscreen():
    """Make the development launcher start the game full-screen.

    The engine ignores window resize requests for its 800x600 render target, so
    the only way to get a usable debug view is the game's own screen mode.
    Set ESCHALON_WINDOWED=1 to keep the player's windowed preference.
    """
    if os.environ.get("ESCHALON_WINDOWED") == "1":
        return "windowed (ESCHALON_WINDOWED=1)"
    if not SCREEN_CFG.exists():
        return "screen config missing; leaving game default"
    lines = [
        line.rstrip("\r")
        for line in SCREEN_CFG.read_text(encoding="ascii", errors="ignore").splitlines()
    ]
    changes = []
    for index, line in enumerate(lines):
        if index + 1 >= len(lines):
            continue
        value = lines[index + 1].strip()
        if line.startswith("; Screen Mode"):
            if value != "1":
                lines[index + 1] = "1"
                changes.append("screen mode")
        elif line.startswith("; Color Depth"):
            # The game writes 0 while windowed; an invalid depth makes the
            # full-screen switch fail and silently falls back to a window.
            if value not in {"16", "32"}:
                lines[index + 1] = "32"
                changes.append("color depth")
        elif line.startswith("; Screen Refresh"):
            if not value.isdigit() or int(value) <= 0:
                lines[index + 1] = "60"
                changes.append("refresh rate")
    if not changes:
        return "already full-screen"
    SCREEN_CFG.write_text("\r\n".join(lines) + "\r\n", encoding="ascii", newline="")
    return "adjusted: " + ", ".join(changes)


def _read_first_column(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] for row in csv.reader(stream) if row]


def _add_paragraph_variants(mapping, source, target):
    """Add per-paragraph keys for bodies the engine splits before display.

    Narrative entries separate paragraphs with '*'.  Some display paths hand
    the wrapper a single paragraph instead of the complete body, so map every
    matching paragraph pair as well.  Existing whole-body keys always win.
    """
    if "*" not in source or "*" not in target:
        return 0
    source_parts = [part.strip() for part in source.split("*")]
    target_parts = [part.strip() for part in target.split("*")]
    if len(source_parts) != len(target_parts):
        return 0
    added = 0
    for part_source, part_target in zip(source_parts, target_parts):
        if len(part_source) < 8 or not part_target or part_source == part_target:
            continue
        if part_source not in mapping:
            mapping[part_source] = part_target
            added += 1
    return added


_TAIL_NOISE = re.compile(r'["\'\)\]]\s?[A-Za-z0-9<>]$')
_NAME_SLOT = re.compile(r'(?:^|[\s"“”\'\(\[:;,.!?])\$(?=$|[\s"“”\'\)\]:;,.!?])')


def _add_tail_alias(mapping, source, target):
    """Drop branch-id letters the extractor appended after closing quotes.

    Script records such as ``"...for me?"D`` carry a one-letter branch id that
    the game itself never displays, so the runtime string lacks it.  Register
    the cleaned variant as an alias while keeping the original key.
    """
    if len(source) < 4 or not _TAIL_NOISE.search(source):
        return 0
    alias = source[:-1].rstrip()
    if not alias or alias in mapping:
        return 0
    clean_target = target
    if clean_target.endswith(source[-1]):
        clean_target = clean_target[:-1].rstrip()
    mapping[alias] = clean_target
    return 1


def _build_name_patterns(mapping):
    """Entries with a player-name slot cannot match after the name is filled in.

    Only the common case is handled: one trailing ``$`` slot followed by at
    most a short suffix.  The runtime name is recovered from the prefix and
    suffix boundaries instead of a regex, so embedded line breaks stay safe.
    """
    patterns = []
    for source, target in mapping.items():
        if source.count("$") != 1 or target.count("$") != 1:
            continue
        if not _NAME_SLOT.search(source):
            continue
        prefix, suffix = source.split("$", 1)
        target_prefix, target_suffix = target.split("$", 1)
        if len(prefix) < 8 or len(suffix) > 8:
            continue
        patterns.append(
            {
                "prefix": prefix,
                "suffix": suffix,
                "target": target_prefix + "\u0001" + target_suffix,
            }
        )
        # Dialogue panels render one wrapped line at a time; the name slot is
        # usually on the final sentence. Register that sentence as its own
        # pattern so the wrapped line can be recovered on its own.
        tail_prefix = re.split(r"\n|(?<=[.!?])\s+", prefix)[-1]
        tail_target = re.split(r"\n|。", target_prefix)[-1]
        if len(tail_prefix) >= 10 and tail_target and tail_prefix != prefix:
            patterns.append(
                {
                    "prefix": tail_prefix,
                    "suffix": suffix,
                    "target": tail_target + "\u0001" + target_suffix,
                }
            )
    return patterns


def load_offline_mapping():
    """Load the original corpus plus the unified, fully local translation pair."""
    mapping = {
        source: target
        for source, target in core.load_mapping().items()
        if "\ufffd" not in target
    }
    offline_entries = 0
    def merge_csv_pair(source_path, translated_path, label):
        nonlocal offline_entries
        originals = _read_first_column(source_path)
        translations = _read_first_column(translated_path)
        if len(originals) != len(translations):
            raise RuntimeError(
                f"{label} CSV row count mismatch: "
                f"{len(originals)} source vs {len(translations)} translated"
            )
        for source, target in zip(originals, translations):
            if source and target and source != target:
                runtime_source = source.replace("\\n", "\n")
                runtime_target = target.replace("\\n", "\n")
                mapping[runtime_source] = runtime_target
                # Map records store object descriptions without the game's
                # generated observation prefix.  Build these deterministic
                # display strings from the static corpus instead of learning
                # each object at runtime.
                if runtime_source.lower().startswith(("a ", "an ", "the ")):
                    mapping["You see " + runtime_source] = "你看见" + runtime_target
                _add_paragraph_variants(mapping, runtime_source, runtime_target)
                _add_tail_alias(mapping, runtime_source, runtime_target)
                offline_entries += 1

    if OFFLINE_SOURCE.exists() and OFFLINE_TRANSLATED.exists():
        merge_csv_pair(OFFLINE_SOURCE, OFFLINE_TRANSLATED, "Offline corpus")
    override_entries = 0
    if RUNTIME_OVERRIDES.exists():
        with RUNTIME_OVERRIDES.open("r", encoding="utf-8") as stream:
            overrides = json.load(stream)
        if not isinstance(overrides, dict) or not all(
            isinstance(source, str) and isinstance(target, str)
            for source, target in overrides.items()
        ):
            raise RuntimeError("Runtime override file must be a JSON object of string pairs")
        for source, target in overrides.items():
            if source and target and source != target:
                mapping[source] = target
                override_entries += 1
    return mapping, offline_entries, override_entries


def _build_prefix_index(mapping):
    """Index paragraphs by their first two words.

    Dialogue panels receive one wrapped line at a time, so the full paragraph
    never reaches a hook.  Keying paragraphs by their opening words lets the
    runtime recognise the first line of a paragraph and split the translation
    proportionally across the following lines.

    Short options matter as much as long paragraphs: a 24-character reply is
    still a full dialogue line, so only truly trivial keys are skipped.
    """
    index = {}
    for source in mapping:
        if len(source) < 12 or "\ufffd" in source:
            continue
        words = source.split()[:2]
        if len(words) < 2:
            continue
        token = " ".join(words)
        if len(token) < 6:
            continue
        index.setdefault(token, []).append(source)
    return index


def _build_word_index(mapping):
    """Index paragraphs by a few distinctive words.

    Dialogue and option text is wrapped into ~50-character fragments before it
    reaches the drawing call, so a fragment never equals a stored key and often
    starts mid-sentence. Looking a fragment up by its rarest words lets the
    runtime find the owning paragraph and slice the translation from there.

    A five-letter floor is deliberate: sentences such as
    "No way. I'm not going to risk my life for a chunk of metal." contain no
    six-letter word at all and would otherwise be unreachable. The per-word
    cap is high because common words appear in far more than forty paragraphs,
    and dropping them removes the only handle the lookup has.
    """
    index = {}
    for source in mapping:
        if len(source) < 12 or "\ufffd" in source:
            continue
        compact = re.sub(r"\s+", " ", source).strip()
        words = {word.lower() for word in re.findall(r"[A-Za-z][A-Za-z']{4,}", compact)}
        if not words:
            continue
        for word in sorted(words, key=len, reverse=True)[:8]:
            index.setdefault(word, []).append(source)
    return {word: items for word, items in index.items() if len(items) <= 200}


def build_hook_script(mapping):
    mapping_json = json.dumps(mapping, ensure_ascii=False, separators=(",", ":"))
    name_patterns_json = json.dumps(
        _build_name_patterns(mapping), ensure_ascii=False, separators=(",", ":")
    )
    prefix_index_json = json.dumps(
        _build_prefix_index(mapping), ensure_ascii=False, separators=(",", ":")
    )
    word_index_json = json.dumps(
        _build_word_index(mapping), ensure_ascii=False, separators=(",", ":")
    )
    return f"""
'use strict';

const translations = {mapping_json};
const namePatterns = {name_patterns_json};
const prefixIndex = {prefix_index_json};
const wordIndex = {word_index_json};
let dialogParagraph = null;
// UI counters such as "2.3/136 lbs" are drawn between dialogue lines and used
// to reset the paragraph immediately, which orphaned the final wrapped line.
// Tolerate a few unrelated draws before dropping the context.
let dialogMisses = 0;

// Dialogue panels hand the drawing call one wrapped line at a time, so the text
// never equals a stored paragraph. Recognise the owning paragraph, then return
// the proportional Chinese slice for that line. The engine also rewrites the
// ASCII apostrophe to control byte 0x19 and doubles spaces, so all comparisons
// run on this folded form.
function normalizeText(value) {{
    return value
        .replace(/[\\u0019\\u2018\\u2019]/g, "'")
        .replace(/[\\u001c\\u001d\\u201c\\u201d]/g, '"')
        .replace(/[\\u0000-\\u0008\\u000b\\u000c\\u000e-\\u0018\\u001a-\\u001f]/g, '')
        .replace(/\\s+/g, ' ')
        .trim();
}}

function stripRecordQuotes(value) {{
    return value
        .replace(/^[\\s"'\\[]+/, '')
        .replace(/[\\s"'\\]]+$/, '')
        .trim();
}}

function paragraphSlice(paragraph, position, length) {{
    const total = paragraph.normText.length;
    const target = paragraph.translated;
    if (!total || !target.length) return undefined;
    const start = Math.round(position / total * target.length);
    const end = Math.round((position + length) / total * target.length);
    const slice = target.slice(start, Math.max(end, start + 1))
        .replace(/[\\r\\n*]+/g, ' ').trim();
    if (!slice.length) return undefined;
    paragraph.consumed = position + length;
    return slice;
}}

function findParagraphByFragment(line) {{
    const words = (line.match(/[A-Za-z][A-Za-z']{{5,}}/g) || []).map(word => word.toLowerCase());
    if (!words.length) return undefined;
    words.sort((a, b) => b.length - a.length);
    for (const word of words.slice(0, 5)) {{
        const list = wordIndex[word];
        if (list === undefined) continue;
        for (const source of list) {{
            const target = translations[source];
            if (target === undefined) continue;
            const normSource = normalizeText(source);
            const position = normSource.indexOf(line);
            if (position < 0) continue;
            const paragraph = {{normText: normSource, translated: target, consumed: 0}};
            const slice = paragraphSlice(paragraph, position, line.length);
            if (slice === undefined) continue;
            dialogParagraph = paragraph;
            return slice;
        }}
    }}
    return undefined;
}}

function translateDialogLine(text) {{
    const line = normalizeText(text);
    if (line.length < 3) return undefined;
    if (dialogParagraph !== null) {{
        const window = Math.max(0, dialogParagraph.consumed - 80);
        const position = dialogParagraph.normText.indexOf(line, window);
        if (position >= 0) {{
            dialogMisses = 0;
            return paragraphSlice(dialogParagraph, position, line.length);
        }}
        // The trailing quote of the final line is part of the record, not the
        // stored paragraph, so retry the same line without record punctuation.
        const bareTail = stripRecordQuotes(line);
        if (bareTail.length >= 3 && bareTail !== line) {{
            const tailPosition = dialogParagraph.normText.indexOf(bareTail, window);
            if (tailPosition >= 0) {{
                dialogMisses = 0;
                return paragraphSlice(dialogParagraph, tailPosition, bareTail.length);
            }}
        }}
        // Keep the paragraph for the next line, but do not hold it forever.
        dialogMisses++;
        if (dialogMisses >= 4) {{
            dialogParagraph = null;
            dialogMisses = 0;
        }}
    }}
    const bare = stripRecordQuotes(line);
    if (bare.length >= 6) {{
        const slice = findParagraphByFragment(bare);
        if (slice !== undefined) return slice;
    }}
    // Quote-stripped form matches the stored keys. Options reach draw as
    // '"No way. ..."' while the corpus stores them without the record quotes,
    // and a quoted first token never matches the prefix index.
    const words = bare.split(' ').slice(0, 2).join(' ');
    const candidates = prefixIndex[words] || prefixIndex[line.split(' ').slice(0, 2).join(' ')];
    if (candidates === undefined) return undefined;
    for (const source of candidates) {{
        const normSource = normalizeText(source);
        if (!normSource.startsWith(bare)) continue;
        const target = translations[source];
        if (target === undefined) continue;
        const paragraph = {{normText: normSource, translated: target, consumed: 0}};
        const slice = paragraphSlice(paragraph, 0, line.length);
        if (slice === undefined) continue;
        dialogParagraph = paragraph;
        return slice;
    }}
    return undefined;
}}
const normalizedIndex = new Map();
for (const key of Object.keys(translations)) {{
    const compact = normalizeText(key);
    if (compact.length >= 2 && !normalizedIndex.has(compact)) normalizedIndex.set(compact, key);
}}

// The engine substitutes the player's name into '$' slots before display, so
// these entries can never match a stored key. Recover the name from the fixed
// prefix and suffix boundaries and substitute it into the translation.
function applyNamePattern(source) {{
    for (const item of namePatterns) {{
        if (source.length <= item.prefix.length + item.suffix.length) continue;
        if (!source.startsWith(item.prefix) || !source.endsWith(item.suffix)) continue;
        const name = source.slice(item.prefix.length, source.length - item.suffix.length);
        if (!name || name.length > 32) continue;
        return item.target.split('\\u0001').join(name);
    }}
    return undefined;
}}

function lookupTranslation(source) {{
    let target = translations[source];
    if (target === undefined) target = translations[source.trim()];
    if (target === undefined) {{
        const key = normalizedIndex.get(normalizeText(source));
        if (key !== undefined) target = translations[key];
    }}
    if (target === undefined) target = applyNamePattern(source);
    return target;
}}

// A narrative body can reach the wrapper either as the complete text or as
// one paragraph after the engine split it at '*'. Try the whole body first,
// then translate every paragraph and reassemble them in display order.
function lookupParagraph(source) {{
    const direct = lookupTranslation(source);
    if (direct !== undefined) return direct;
    const parts = source.split('*');
    if (parts.length < 2) return undefined;
    const translated = [];
    let hits = 0;
    for (const part of parts) {{
        const key = part.trim();
        const value = key.length >= 8 ? lookupTranslation(key) : undefined;
        if (value === undefined) translated.push(key);
        else {{ translated.push(value); hits++; }}
    }}
    return hits ? translated.join('\\n') : undefined;
}}

const phrases = Object.keys(translations)
    // Never inject dictionary-scale translations into a longer English
    // sentence. The game word-wraps descriptions at draw time; replacing
    // "the" or "of" inside such a fragment creates unusable mixed text.
    .filter(key => key.length >= 16 && key.length <= 240 && /[A-Za-z]/.test(key))
    .sort((a, b) => b.length - a.length);
const unsafeStandaloneWords = new Set([
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'in',
    'is', 'it', 'of', 'on', 'or', 'that', 'the', 'this', 'to', 'was',
    'with', 'you', 'your'
]);
const retained = new Map();
const resolved = new Map();
const unmatched = new Set();
const stackSignatures = new Set();
const paragraphSeen = new Set();
const moduleBase = Process.mainModule.base;
let hitCount = 0;

function readBlitzString(value) {{
    if (value.isNull()) return null;
    const length = value.add(8).readU32();
    if (length > 65535) return null;
    return value.add(12).readUtf16String(length);
}}

function makeBlitzString(text) {{
    let value = retained.get(text);
    if (value !== undefined) return value;
    const bytes = 12 + (text.length + 1) * 2;
    value = Memory.alloc(bytes);
    value.writePointer(ptr('0x{BLITZ_STRING_TYPE:08X}'));
    value.add(4).writeU32(0x80000000);
    value.add(8).writeU32(text.length);
    value.add(12).writeUtf16String(text);
    retained.set(text, value);
    return value;
}}

function isWordChar(char) {{
    return char !== undefined && /[A-Za-z0-9_]/.test(char);
}}

function replaceVisiblePhrases(source) {{
    let result = source;
    let replacements = 0;
    for (const phrase of phrases) {{
        let cursor = 0;
        while (true) {{
            const index = result.indexOf(phrase, cursor);
            if (index < 0) break;
            const before = index > 0 ? result[index - 1] : undefined;
            const afterIndex = index + phrase.length;
            const after = afterIndex < result.length ? result[afterIndex] : undefined;
            const leftOkay = !isWordChar(phrase[0]) || !isWordChar(before);
            const rightOkay = !isWordChar(phrase[phrase.length - 1]) || !isWordChar(after);
            if (!leftOkay || !rightOkay) {{
                cursor = index + phrase.length;
                continue;
            }}
            const target = translations[phrase];
            result = result.slice(0, index) + target + result.slice(afterIndex);
            cursor = index + target.length;
            replacements++;
        }}
    }}
    return replacements ? result : undefined;
}}

function makeChineseBreakable(text) {{
    // This screen's native wrapper only wraps at ASCII spaces. Add sparse
    // break opportunities to long Han runs while keeping normal prose intact.
    return text.replace(/[\\u3400-\\u9fff]{{7,}}/g, run =>
        run.match(/.{{1,6}}/g).join(' '));
}}

// Combat and service messages are assembled at runtime from names, verbs and
// numbers, so they never match a whole-sentence dictionary entry. Normalise
// the recurring English fragments after the dictionary lookups.
function applyCombatPatterns(text) {{
    let out = text;
    out = out.replace(/\\b(\\d+)\\s+points?\\s+of\\s+damage\\b/gi, '$1 点伤害');
    out = out.replace(/\\bpoints?\\s+of\\s+damage\\b/gi, '点伤害');
    out = out.replace(/\\bsuffers\\b/gi, '承受');
    out = out.replace(/\\battacks\\b/gi, '攻击');
    out = out.replace(/\\bmisses\\b/gi, '未命中');
    out = out.replace(/\\bhits\\b/gi, '命中');
    out = out.replace(/\\bfor\\s+(\\d+)\\s+damage\\b/gi, '造成 $1 点伤害');
    out = out.replace(/\\byou\\s+gain\\s+(\\d+)\\s+experience\\b/gi, '获得 $1 点经验');
    out = out.replace(/\\bgains?\\s+(\\d+)\\s+experience\\b/gi, '获得 $1 点经验');
    out = out.replace(/\\bTown Guard\\b/g, '城镇守卫');
    // Character sheet header: "Level: 1 (Layman)". The class name is a corpus
    // entry of its own, so reuse it instead of duplicating every combination.
    out = out.replace(/^Level:\\s*(\\d+)\\s*\\(([^)]+)\\)\\s*$/i, (match, level, cls) => {{
        const name = translations[cls] || translations[cls.trim()] || cls;
        return '等级：' + level + '（' + name + '）';
    }});
    // Play-time strings: "9.6 hours".
    out = out.replace(/(\\d+(?:\\.\\d+)?)\\s*hours?\\b/gi, '$1 小时');
    // Save-slot timestamps: "21 Jul 2026  22:41:06".
    const months = {{
        Jan: '1月', Feb: '2月', Mar: '3月', Apr: '4月', May: '5月', Jun: '6月',
        Jul: '7月', Aug: '8月', Sep: '9月', Oct: '10月', Nov: '11月', Dec: '12月'
    }};
    out = out.replace(
        /\\b(\\d{{1,2}})\\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+(\\d{{4}})\\b/g,
        (match, day, mon, year) => year + '年' + months[mon] + day + '日');
    // Race plus class label drawn as one short string: "Druidic Rogue".
    // Only exact two-word strings qualify, so prose cannot be affected.
    const pair = out.trim().split(/\\s+/);
    if (pair.length === 2) {{
        const race = translations[pair[0]];
        const klass = translations[pair[1]];
        if (race !== undefined && klass !== undefined) out = race + ' ' + klass;
    }}
    if (out !== text && /[\\u3400-\\u9fff]/.test(out) && /\\.\\s*$/.test(out)) {{
        out = out.replace(/\\.\\s*$/, '。');
    }}
    return out === text ? undefined : out;
}}

// Ghidra: FUN_004c69ad (0x4C69AD) builds the full narrative body, splits it
// into '|' command and prose parts, and then picks the parchment panel.
// At 0x4c6c53 every panel branch has converged: [ebp-0x24] still holds the
// complete prose String and the earlier 600-character panel decision has
// already been evaluated into eax. Replacing the slot here therefore cannot
// change which panel the native code selects.
let lastNarrativeEntry = '';
Interceptor.attach(ptr('0x4C69AD'), {{
    onEnter(args) {{
        try {{
            const signature = args[0].toInt32() + ':' + args[1].toInt32() + ':' + args[2].toInt32();
            if (signature !== lastNarrativeEntry) {{
                lastNarrativeEntry = signature;
                send({{kind: 'narrative_entry', signature}});
            }}
        }} catch (error) {{}}
    }}
}});

Interceptor.attach(ptr('0x{NARRATIVE_PREWRAP_VA:08X}'), {{
    onEnter() {{
        try {{
            const slot = this.context.ebp.sub(0x24);
            const source = readBlitzString(slot.readPointer());
            if (source === null || source.length < 2) return;
            if (/[\\u3400-\\u9fff]/.test(source)) return;
            let target = lookupParagraph(source);
            if (target === undefined) {{
                send({{kind: 'paragraph', source}});
                return;
            }}
            if (target === source) return;
            target = makeChineseBreakable(target);
            slot.writePointer(makeBlitzString(target));
            send({{kind: 'narrative_hit', source: source.slice(0, 100),
                  target: target.slice(0, 100)}});
        }} catch (error) {{
            send({{kind: 'hook_error', message: 'narrative: ' + String(error)}});
        }}
    }}
}});

// The game funnels message-log prose through this routine while it is still
// one complete BlitzMax String.  The routine then wraps it into 545-pixel
// line objects stored in off_59CDCC.  Translating arg0 here makes the native
// engine wrap Chinese and avoids encounter-specific draw-fragment overrides.
Interceptor.attach(ptr('0x{MESSAGE_PREWRAP_VA:08X}'), {{
    onEnter(args) {{
        try {{
            const source = readBlitzString(args[0]);
            if (source === null || source.length < 2) return;
            let target = translations[source];
            if (target === undefined) target = translations[source.trim()];
            if (target === undefined) target = replaceVisiblePhrases(source);
            const baseText = target === undefined ? source : target;
            const patched = applyCombatPatterns(baseText);
            if (patched !== undefined) target = patched;
            if (target === undefined || target === source) return;
            target = makeChineseBreakable(target);
            args[0] = makeBlitzString(target);
            send({{kind: 'prewrap_hit', source: source.slice(0, 100),
                  target: target.slice(0, 100)}});
        }} catch (error) {{
            send({{kind: 'hook_error', message: 'prewrap: ' + String(error)}});
        }}
    }}
}});

// Confirmation/help panels use a separate formatter. arg0 enters this
// routine as one complete string; the routine subsequently handles ^/& style
// markers and draws the paragraph one English word at a time. Translate at
// entry so every panel backed by the offline CSV is covered before splitting.
Interceptor.attach(ptr('0x{POPUP_PREWRAP_VA:08X}'), {{
    onEnter(args) {{
        try {{
            const source = readBlitzString(args[0]);
            if (source === null || source.length < 2) return;
            let target = translations[source];
            if (target === undefined) target = translations[source.trim()];
            if (target === undefined) target = replaceVisiblePhrases(source);
            const baseText = target === undefined ? source : target;
            const patched = applyCombatPatterns(baseText);
            if (patched !== undefined) target = patched;
            if (target === undefined || target === source) return;
            target = makeChineseBreakable(target);
            args[0] = makeBlitzString(target);
            send({{kind: 'popup_hit', source: source.slice(0, 100),
                  target: target.slice(0, 100)}});
        }} catch (error) {{
            send({{kind: 'hook_error', message: 'popup: ' + String(error)}});
        }}
    }}
}});

// Character creation / skill help stores the complete description at
// [ebp-0x4c], then splits it character-by-character at 0x4D9524.
Interceptor.attach(ptr('0x{SKILL_PARAGRAPH_VA:08X}'), {{
    onEnter() {{
        try {{
            const slot = this.context.ebp.sub(0x4c);
            const source = readBlitzString(slot.readPointer());
            if (source === null || source.length < 2) return;
            if (/[A-Za-z]/.test(source) && !paragraphSeen.has(source)) {{
                paragraphSeen.add(source);
                send({{kind: 'paragraph', source}});
            }}
            let target = translations[source];
            if (target === undefined) target = translations[source.trim()];
            if (target === undefined || target === source) return;
            target = makeChineseBreakable(target);
            slot.writePointer(makeBlitzString(target));
            send({{kind: 'paragraph_hit', source: source.slice(0, 80),
                  target: target.slice(0, 80)}});
        }} catch (error) {{
            send({{kind: 'hook_error', message: 'paragraph: ' + String(error)}});
        }}
    }}
}});

Interceptor.attach(ptr('0x{DRAW_TEXT_VA:08X}'), {{
    onEnter(args) {{
        try {{
            const source = readBlitzString(args[1]);
            if (source === null) return;
            let target;
            if (resolved.has(source)) {{
                target = resolved.get(source);
            }} else {{
                target = translations[source];
                if (unsafeStandaloneWords.has(source.trim().toLowerCase())) {{
                    target = undefined;
                }}
                if (target === undefined) target = translations[source.trim()];
                if (unsafeStandaloneWords.has(source.trim().toLowerCase())) {{
                    target = undefined;
                }}
                if (target === undefined) target = lookupTranslation(source);
                if (unsafeStandaloneWords.has(source.trim().toLowerCase())) {{
                    target = undefined;
                }}
                if (target === undefined && source.length >= 12 && source.indexOf(' ') > 0) {{
                    target = translateDialogLine(source);
                }}
                // Phrase substitution only suits short labels; on wrapped prose it
                // would translate a fragment and leave the rest in English.
                if (target === undefined && source.length <= 120) {{
                    target = replaceVisiblePhrases(source);
                }}
                const baseText = target === undefined ? source : target;
                const patched = applyCombatPatterns(baseText);
                if (patched !== undefined) target = patched;
                resolved.set(source, target === undefined ? null : target);
            }}
            if (target === null) target = undefined;
            if (target === undefined && /[A-Za-z]/.test(source) && !unmatched.has(source)) {{
                unmatched.add(source);
                if (unmatched.size <= 2000) {{
                    send({{kind: 'unmatched', source}});
                }}
                // Dialogue bodies and other panels are wrapped before drawing.
                // Record distinct native call paths for multi-word fragments so
                // the panel formatter can be identified from the call stack.
                if (source.length > 32 && source.indexOf(' ') > 0 && stackSignatures.size < 40) {{
                    const stack = Thread.backtrace(this.context, Backtracer.ACCURATE)
                        .slice(0, 16)
                        .map(address => address.sub(moduleBase).toString());
                    const signature = stack.slice(0, 8).join(',');
                    if (!stackSignatures.has(signature)) {{
                        stackSignatures.add(signature);
                        send({{kind: 'callstack', source, stack}});
                    }}
                }}
            }}
            if (target === undefined || target === source) return;
            args[1] = makeBlitzString(target);
            hitCount++;
            if (hitCount <= 20) {{
                send({{kind: 'hit', source: source.slice(0, 80), target: target.slice(0, 80)}});
            }}
        }} catch (error) {{
            send({{kind: 'hook_error', message: String(error)}});
        }}
    }}
}});

send({{kind: 'ready', entries: Object.keys(translations).length}});
"""


def on_message(message, _data):
    if message.get("type") == "error":
        print("Display hook error:", message.get("description"), file=sys.stderr)
        return
    payload = message.get("payload", {})
    kind = payload.get("kind")
    if kind == "ready":
        print(f"Display hook ready: {payload.get('entries')} translations")
    elif kind == "dialog_entry":
        print(f"Dialog render entry: object=0x{payload.get('pointer', 0):08x}")
    elif kind == "dialog_candidate":
        print(f"Dialog candidate +0x{payload.get('offset', 0):x} (depth {payload.get('depth')}): "
              f"{payload.get('source', '')}")
    elif kind == "dialog_hit":
        print(f"Dialog text replaced at +0x{payload.get('offset', 0):x}: "
              f"{payload.get('source', '')}")
    elif kind == "narrative_entry":
        signature = payload.get("signature", "")
        print(f"Narrative call (id:type:panel) = {signature}")
        with NARRATIVE_CALL_LOG.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"call": signature}, ensure_ascii=False) + "\n")
    elif kind == "hit":
        print(f"Translated on screen: {payload.get('source')!r} -> {payload.get('target')!r}")
    elif kind == "prewrap_hit":
        print(
            "Translated before wrapping: "
            f"{payload.get('source')!r} -> {payload.get('target')!r}"
        )
    elif kind == "popup_hit":
        print(
            "Translated popup before wrapping: "
            f"{payload.get('source')!r} -> {payload.get('target')!r}"
        )
    elif kind == "hook_error":
        print("Display hook callback error:", payload.get("message"), file=sys.stderr)
    elif kind == "unmatched":
        source = payload.get("source", "")
        with UNTRANSLATED_LOG.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"text": source}, ensure_ascii=False) + "\n")
    elif kind == "callstack":
        record = {"text": payload.get("source", ""), "stack": payload.get("stack", [])}
        with CALLSTACK_LOG.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    elif kind == "paragraph":
        source = payload.get("source", "")
        with PARAGRAPH_LOG.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"text": source}, ensure_ascii=False) + "\n")
    elif kind in {"paragraph_hit", "narrative_hit"}:
        print(f"Translated paragraph: {payload.get('source')!r} -> {payload.get('target')!r}")


def main():
    required = [core.EXE, core.ORIGINAL_CSV, core.TRANSLATED_CSV, *core.FONT_FILES]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("Missing required files:\n" + "\n".join(missing), file=sys.stderr)
        return 2

    mapping, offline_entries, override_entries = load_offline_mapping()
    UNTRANSLATED_LOG.write_text("", encoding="utf-8")
    CALLSTACK_LOG.write_text("", encoding="utf-8")
    PARAGRAPH_LOG.write_text("", encoding="utf-8")
    NARRATIVE_CALL_LOG.write_text("", encoding="utf-8")
    print(f"Loaded {len(mapping)} translations")
    if OFFLINE_SOURCE.exists():
        print(f"Offline corpus active: {offline_entries} translated entries")
    if override_entries:
        print(f"Runtime fragment overrides active: {override_entries}")
    print(f"Screen mode: {ensure_fullscreen()}")
    app_id_file = core.ensure_steam_identity()
    print(f"Steam identity ready: {app_id_file}")
    copied_exe = None
    if os.environ.get("ESCHALON_COPY_EXE") == "1":
        copied_exe = core.prepare_injectable_executable()
        print(f"Prepared local runtime copy: {copied_exe}")
    pi = core.launch_suspended()
    print(f"Game PID: {pi.dwProcessId}")
    session = None
    script = None
    try:
        fonts = core.patch_fonts(pi.hProcess)
        for name, address, size in fonts:
            print(f"Font {name}: 0x{address:08X}, {size:,} bytes")

        # No embedded text tables are changed. In particular, item names stay
        # English internally so containers, maps, scripts and saves remain valid.
        print("Game data patches: disabled (safe display-layer mode)")
        core.k32.ResumeThread(pi.hThread)

        session = frida.attach(pi.dwProcessId)
        script = session.create_script(build_hook_script(mapping))
        script.on("message", on_message)
        script.load()
        print("Chinese runtime started. Close the game to exit this launcher.")
        core.k32.WaitForSingleObject(pi.hProcess, core.INFINITE)
    except Exception:
        core.k32.TerminateProcess(pi.hProcess, 1)
        raise
    finally:
        if session is not None:
            try:
                session.detach()
            except frida.InvalidOperationError:
                pass
        core.k32.CloseHandle(pi.hThread)
        core.k32.CloseHandle(pi.hProcess)
        core.cleanup_injectable_executable(copied_exe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
