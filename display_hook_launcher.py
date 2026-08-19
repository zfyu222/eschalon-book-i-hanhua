"""Eschalon Book I Chinese launcher using a display-layer text hook.

The game uses item names as both visible labels and internal identifiers.
Changing the embedded item table therefore breaks map/container lookups.
This launcher leaves all game data untouched and replaces only the BlitzMax
String passed to brl.max2d.TImageFont.Draw (VA 0x477B47).
"""
import csv
import json
import sys
from pathlib import Path

import frida

import launch_chinese as base


core = base.core
DRAW_TEXT_VA = 0x477B47
MESSAGE_PREWRAP_VA = 0x4BDEB8
POPUP_PREWRAP_VA = 0x4C4982
SKILL_PARAGRAPH_VA = 0x4D950F
BLITZ_STRING_TYPE = 0x4F1CB0
UNTRANSLATED_LOG = Path(__file__).resolve().parent / "runtime_untranslated.jsonl"
CALLSTACK_LOG = Path(__file__).resolve().parent / "runtime_callstacks.jsonl"
PARAGRAPH_LOG = Path(__file__).resolve().parent / "runtime_paragraphs.jsonl"
OFFLINE_SOURCE = Path(__file__).resolve().parent / "eschalonbook_text.csv"
OFFLINE_TRANSLATED = Path(__file__).resolve().parent / "eschalonbook_text_translated.csv"
RUNTIME_OVERRIDES = Path(__file__).resolve().parent / "runtime_fragment_overrides.json"


def _read_first_column(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] for row in csv.reader(stream) if row]


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


def build_hook_script(mapping):
    mapping_json = json.dumps(mapping, ensure_ascii=False, separators=(",", ":"))
    return f"""
'use strict';

const translations = {mapping_json};
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
                if (target === undefined) target = replaceVisiblePhrases(source);
                resolved.set(source, target === undefined ? null : target);
            }}
            if (target === null) target = undefined;
            if (target === undefined && /[A-Za-z]/.test(source) && !unmatched.has(source)) {{
                unmatched.add(source);
                if (unmatched.size <= 2000) {{
                    send({{kind: 'unmatched', source}});
                }}
                // Long descriptions are rendered one English word at a time.
                // Record a few distinct native call paths so IDA can identify
                // the game's word-wrap routine above brl.max2d.DrawText.
                if (source.length <= 32 && stackSignatures.size < 24) {{
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
    elif kind == "paragraph_hit":
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
    print(f"Loaded {len(mapping)} translations")
    if OFFLINE_SOURCE.exists():
        print(f"Offline corpus active: {offline_entries} translated entries")
    if override_entries:
        print(f"Runtime fragment overrides active: {override_entries}")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
