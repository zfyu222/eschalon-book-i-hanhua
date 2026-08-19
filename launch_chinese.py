"""Final Eschalon Book I Chinese launcher."""
import struct

import cn_launcher as production

core = production.core


def parse_csv_line_preserving_quotes(line):
    columns, current, quoted = [], [], False
    for char in line:
        if char == '"':
            quoted = not quoted
            current.append(char)
        elif char == "," and not quoted:
            columns.append("".join(current)); current = []
        else:
            current.append(char)
    columns.append("".join(current))
    return columns


def patch_items(process, mapping):
    address, payload_size = 0x54159C, 39851
    text = core.read_memory(process, address, payload_size).decode("utf-8")
    output, count = [], 0
    for line in text.split("\r\n"):
        if not line.strip():
            output.append(line); continue
        columns = parse_csv_line_preserving_quotes(line)
        if len(columns) >= 2:
            item_name = columns[1].strip('"')
            if item_name and item_name != "DESCRIPTION" and item_name in mapping:
                columns[1] = f'"{mapping[item_name]}"'
                line = ",".join(columns)
                count += 1
        output.append(line)
    encoded = "\r\n".join(output).encode("utf-8")
    if len(encoded) > payload_size:
        raise RuntimeError(f"translated item table overflow: {len(encoded)} > {payload_size}")
    core.write_memory(process, address, encoded + b"\0" * (payload_size - len(encoded)))
    return count


def patch_fonts(process):
    allocations = []
    for path, code_va in zip(core.FONT_FILES, core.FONT_CODE_VAS):
        data = path.read_bytes()
        address = core.k32.VirtualAllocEx(process, None, len(data),
                                          core.MEM_COMMIT | core.MEM_RESERVE,
                                          core.PAGE_READWRITE)
        if not address:
            core.win_error("VirtualAllocEx(font)")
        core.write_memory(process, address, data)
        # 0x465A81 registers resources as (original_end_key, data_ptr, size).
        # Keep push-original_end at code_va+17 unchanged because later lookups
        # use that key. Only redirect data_ptr and the arithmetic operands used
        # to calculate size.
        for offset, value in ((1, address + len(data)), (6, address), (12, address)):
            core.write_memory(process, code_va + offset, struct.pack("<I", value), executable=True)
        allocations.append((path.name, address, len(data)))
    return allocations


core.patch_items = patch_items
core.patch_fonts = patch_fonts
_patch_fixed_slot_strings = core.patch_short_strings


# These blocks are registered by the executable during bootstrap.  The last
# immediate in each registration sequence is an identifier used for lookups;
# it must stay unchanged.  The other three operands supply the payload and
# may safely be redirected to an allocation in the target process.
REGISTERED_TEXT_BLOCKS = (
    (0x4907CA, 0x54DC90, 0x55273C),
    (0x49085B, 0x55F0EC, 0x560DB0),
    (0x490943, 0x56B324, 0x56BA5C),
    (0x490A2B, 0x574E84, 0x5753B8),
    (0x490ABC, 0x578E44, 0x579D7C),
    (0x490AD9, 0x579DA4, 0x57B0CC),
    (0x490AF6, 0x57B0F4, 0x57BA48),
    (0x490B13, 0x57BA70, 0x57CA40),
    (0x490BFB, 0x584AAC, 0x585270),
    (0x490C8C, 0x587078, 0x5878D4),
)


def patch_registered_overflows(process, mapping):
    """Redirect registered dialogue resources whose UTF-8 translation grows.

    Replacing a long string in place corrupts the following script command.
    Instead, copy the whole resource block to new memory and update the three
    payload operands in its registration code before the process is resumed.
    """
    changed_sources, blocks, translations = set(), 0, 0
    growing = [(source.encode("utf-8"), target.encode("utf-8"), source)
               for source, target in mapping.items()
               if len(target.encode("utf-8")) > len(source.encode("utf-8"))]
    growing.sort(key=lambda value: len(value[0]), reverse=True)

    for code_va, start, end in REGISTERED_TEXT_BLOCKS:
        payload = core.read_memory(process, start, end - start)
        translated = payload
        matched = []
        for source, target, label in growing:
            if source in translated:
                translated = translated.replace(source, target)
                matched.append(label)
        if not matched:
            continue

        address = core.k32.VirtualAllocEx(
            process, None, len(translated), core.MEM_COMMIT | core.MEM_RESERVE,
            core.PAGE_READWRITE,
        )
        if not address:
            core.win_error("VirtualAllocEx(registered text)")
        core.write_memory(process, address, translated)
        # mov eax,end; sub eax,start; push start.  Do not change +17: it is
        # the original resource key, rather than an end pointer for lookup.
        for offset, value in ((1, address + len(translated)), (6, address), (12, address)):
            core.write_memory(process, code_va + offset, struct.pack("<I", value), executable=True)
        changed_sources.update(matched)
        blocks += 1
        translations += len(matched)

    if blocks:
        print(f"Registered dialogue blocks redirected: {blocks}; long strings: {translations}")
    return changed_sources


def patch_short_strings(process, mapping):
    redirected = patch_registered_overflows(process, mapping)
    # The redirected resources are what the game will subsequently parse;
    # leave their original backing bytes alone.  This also yields a truthful
    # count of strings which still cannot be fitted into their fixed slots.
    remaining = {source: target for source, target in mapping.items() if source not in redirected}
    direct, overflow = _patch_fixed_slot_strings(process, remaining)
    return direct + len(redirected), overflow


# Resource redirection is retained for investigation but is not enabled:
# this build's bootstrap performs additional validation after registration,
# and redirecting those payloads makes the process exit during startup.
core.patch_short_strings = _patch_fixed_slot_strings

if __name__ == "__main__":
    raise SystemExit(core.main())
