"""Corrected launcher entry point with exact embedded-resource boundaries."""
import csv
from io import StringIO

import cn_launcher_v2 as core


def patch_items(process, mapping):
    address, payload_size = 0x54159C, 39851
    text = core.read_memory(process, address, payload_size).decode("utf-8")
    output, count = [], 0
    for line in text.split("\r\n"):
        row = next(csv.reader([line])) if line else []
        if len(row) >= 2 and row[1] in mapping and row[1] != "DESCRIPTION":
            row[1] = mapping[row[1]]
            holder = StringIO()
            csv.writer(holder, lineterminator="").writerow(row)
            line = holder.getvalue()
            count += 1
        output.append(line)
    encoded = "\r\n".join(output).encode("utf-8")
    if len(encoded) > payload_size:
        raise RuntimeError(f"translated item table overflow: {len(encoded)} > {payload_size}")
    core.write_memory(process, address, encoded + b"\0" * (payload_size - len(encoded)))
    return count


def patch_books(process, mapping):
    address, payload_size = 0x552770, 37031
    text = core.read_memory(process, address, payload_size).decode("utf-8")
    count = 0
    for source in sorted(mapping, key=len, reverse=True):
        if len(source) >= 10 and source in text:
            text = text.replace(source, mapping[source])
            count += 1
    encoded = text.encode("utf-8")
    if len(encoded) > payload_size:
        raise RuntimeError(f"translated book table overflow: {len(encoded)} > {payload_size}")
    core.write_memory(process, address, encoded + b"\0" * (payload_size - len(encoded)))
    return count


core.patch_items = patch_items
core.patch_books = patch_books

if __name__ == "__main__":
    raise SystemExit(core.main())
