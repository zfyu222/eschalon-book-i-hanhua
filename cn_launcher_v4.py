"""Final corrected launcher entry point."""
import cn_launcher_v3 as core


def patch_books(process, mapping):
    address, payload_size = 0x552770, 37028
    text = core.core.read_memory(process, address, payload_size).decode("utf-8")
    count = 0
    for source in sorted(mapping, key=len, reverse=True):
        if len(source) >= 10 and source in text:
            text = text.replace(source, mapping[source])
            count += 1
    encoded = text.encode("utf-8")
    if len(encoded) > payload_size:
        raise RuntimeError(f"translated book table overflow: {len(encoded)} > {payload_size}")
    core.core.write_memory(process, address, encoded + b"\0" * (payload_size - len(encoded)))
    return count


core.core.patch_books = patch_books

if __name__ == "__main__":
    raise SystemExit(core.core.main())
