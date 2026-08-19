"""Production launcher: exact resource bounds and fast hard-coded string scan."""
import cn_launcher_v4 as fixed

core = fixed.core.core


def patch_short_strings(process, mapping):
    base, limit = 0x560000, 0x590000
    block = core.read_memory(process, base, limit - base)
    count = overflow = 0
    cursor = 0
    while cursor < len(block):
        end = block.find(b"\0", cursor)
        if end < 0:
            break
        raw = block[cursor:end]
        if len(raw) >= 5:
            source = raw.decode("utf-8", errors="ignore")
            if source in mapping:
                target = mapping[source].encode("utf-8")
                if len(target) <= len(raw):
                    core.write_memory(process, base + cursor,
                                      target + b"\0" * (len(raw) - len(target) + 1))
                    count += 1
                else:
                    overflow += 1
        cursor = end + 1
    return count, overflow


core.patch_short_strings = patch_short_strings

if __name__ == "__main__":
    raise SystemExit(core.main())
