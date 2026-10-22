"""LZW and LZSS compression matching the game's decompressors.

The decompressors are in lib/filebuffer (FileBuffer::DecompressLZW/LZSS, the
same algorithms as in xBaK and BaKGL).

LZW is the Unix `compress` variant: LSB-first bit packing, 9..12-bit codes,
literals 0..255, code 256 resets the table (followed by padding to a group of
n_bits bytes), new entries start at 257. The code width grows when the next
free entry number reaches 1 << n_bits.

LZSS: a flag byte (LSB first); flag 1 - a literal byte, flag 0 - u16 absolute
offset in the output and u8 length - 5.
"""

from __future__ import annotations

CLEAR = 256
FIRST_FREE = 257
MAX_BITS = 12
MAX_ENTRIES = 1 << MAX_BITS


class _BitWriter:
    def __init__(self) -> None:
        self.out = bytearray()
        self.acc = 0
        self.nbits = 0

    def write(self, value: int, n: int) -> None:
        self.acc |= value << self.nbits
        self.nbits += n
        while self.nbits >= 8:
            self.out.append(self.acc & 0xFF)
            self.acc >>= 8
            self.nbits -= 8

    def align(self) -> None:
        if self.nbits:
            self.out.append(self.acc & 0xFF)
            self.acc = 0
            self.nbits = 0

    def zero_bytes(self, n: int) -> None:
        self.out.extend(b"\0" * n)

    def getvalue(self) -> bytes:
        self.align()
        return bytes(self.out)


def compress_lzw(data: bytes, clear_when_full: bool = True) -> bytes:
    """LZW-compress `data`. With clear_when_full the table is reset with code
    256 when it is full (like the original files), otherwise codes stay 12-bit
    and no new entries are added."""
    out = _BitWriter()
    if not data:
        return b""
    table: dict[tuple[int, int], int] = {}
    free = FIRST_FREE
    n_bits = 9
    bitpos = 0  # bits written since the last width change, the first code excluded
    first = True
    full_codes = 0
    w = data[0]
    for c in data[1:]:
        key = (w, c)
        if key in table:
            w = table[key]
            continue
        # emit w
        out.write(w, n_bits)
        if first:
            first = False
        else:
            bitpos += n_bits
        # the decoder adds this entry only when it reads the *next* code, so it
        # widens codes one entry later than the encoder's own table would
        if free < MAX_ENTRIES:
            table[key] = free
            free += 1
            if free > (1 << n_bits) and n_bits < MAX_BITS:
                n_bits += 1
                bitpos = 0
        elif clear_when_full and (full_codes := full_codes + 1) == 2:
            # like the original encoder: one more code with the full table,
            # then the reset
            full_codes = 0
            out.write(CLEAR, n_bits)
            bitpos += n_bits
            out.align()
            group = n_bits << 3
            skip = ((bitpos - 1) + (group - (bitpos - 1 + group) % group)) - bitpos
            out.zero_bytes(skip >> 3)
            table.clear()
            # the decoder spends entry 256 on a dummy for the first code after a
            # reset, so real entries start at 257 again
            free = FIRST_FREE
            n_bits = 9
            bitpos = 0
        w = c
    out.write(w, n_bits)
    return out.getvalue()


def decompress_lzw(data: bytes, size: int) -> bytes:
    """Pure Python port of FileBuffer::DecompressLZW (for tests)."""
    pos = 0  # bit position in data

    def get_bits(n: int) -> int:
        nonlocal pos
        value = 0
        for i in range(n):
            if data[pos >> 3] & (1 << (pos & 7)):
                value |= 1 << i
            pos += 1
        return value

    prefix = [0] * MAX_ENTRIES
    append = [0] * MAX_ENTRIES
    out = bytearray()
    n_bits = 9
    free = FIRST_FREE
    oldcode = get_bits(n_bits)
    lastbyte = oldcode
    bitpos = 0
    out.append(oldcode)
    while (pos + n_bits) <= len(data) * 8 and len(out) < size:
        newcode = get_bits(n_bits)
        bitpos += n_bits
        if newcode == CLEAR:
            pos = (pos + 7) & ~7  # SkipBits
            group = n_bits << 3
            skip = ((bitpos - 1) + (group - (bitpos - 1 + group) % group)) - bitpos
            pos += (skip >> 3) << 3
            n_bits = 9
            free = 256
            bitpos = 0
            continue
        code = newcode
        stack = []
        if code >= free:
            stack.append(lastbyte)
            code = oldcode
        while code >= 256:
            stack.append(append[code])
            code = prefix[code]
        stack.append(code)
        lastbyte = code
        out.extend(reversed(stack))
        if free < MAX_ENTRIES:
            prefix[free] = oldcode
            append[free] = lastbyte
            free += 1
            if free >= (1 << n_bits) and n_bits < MAX_BITS:
                n_bits += 1
                bitpos = 0
        oldcode = newcode
    return bytes(out[:size])


def count_lzw_clears(data: bytes, size: int) -> int:
    """How many reset codes an LZW stream contains (for analysis)."""
    count = 0
    pos = 0
    n_bits = 9
    free = FIRST_FREE
    produced = 1
    bitpos = 0

    def get_bits(n: int) -> int:
        nonlocal pos
        value = 0
        for i in range(n):
            if data[pos >> 3] & (1 << (pos & 7)):
                value |= 1 << i
            pos += 1
        return value

    get_bits(n_bits)
    while (pos + n_bits) <= len(data) * 8 and produced < size:
        code = get_bits(n_bits)
        bitpos += n_bits
        if code == CLEAR:
            count += 1
            pos = (pos + 7) & ~7
            group = n_bits << 3
            skip = ((bitpos - 1) + (group - (bitpos - 1 + group) % group)) - bitpos
            pos += (skip >> 3) << 3
            n_bits = 9
            free = 256
            bitpos = 0
            continue
        produced += 1  # approximate, only to stop at the end
        if free < MAX_ENTRIES:
            free += 1
            if free >= (1 << n_bits) and n_bits < MAX_BITS:
                n_bits += 1
                bitpos = 0
    return count


def compress_lzss(data: bytes) -> bytes:
    """Greedy LZSS: matches of 5..260 bytes at absolute offsets < 65536."""
    out = bytearray()
    i = 0
    index: dict[bytes, list[int]] = {}
    min_len, max_len = 5, 260
    while i < len(data):
        flags_pos = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if i >= len(data):
                break
            best_len, best_off = 0, 0
            key = data[i : i + min_len]
            if len(key) == min_len:
                for start in reversed(index.get(key, [])[-64:]):
                    if start >= 0x10000:
                        continue
                    # no overlapping copies: the decompressor uses memcpy
                    limit = min(max_len, i - start)
                    if limit < min_len:
                        continue
                    length = min_len
                    while (
                        length < limit
                        and i + length < len(data)
                        and data[start + length] == data[i + length]
                    ):
                        length += 1
                    if length > best_len:
                        best_len, best_off = length, start
                        if length == max_len:
                            break
            if best_len >= min_len:
                out += best_off.to_bytes(2, "little") + bytes((best_len - min_len,))
                end = i + best_len
            else:
                flags |= 1 << bit
                out.append(data[i])
                end = i + 1
            while i < end:
                k = data[i : i + min_len]
                if len(k) == min_len:
                    index.setdefault(k, []).append(i)
                i += 1
        out[flags_pos] = flags
    return bytes(out)


def decompress_lzss(data: bytes, size: int) -> bytes:
    """Pure Python port of FileBuffer::DecompressLZSS (for tests)."""
    out = bytearray()
    i = 0
    code = mask = 0
    while i < len(data) and len(out) < size:
        if not mask:
            code = data[i]
            i += 1
            mask = 1
        if code & mask:
            out.append(data[i])
            i += 1
        else:
            offset = data[i] | data[i + 1] << 8
            length = data[i + 2] + 5
            i += 3
            out += out[offset : offset + length]
        mask = (mask << 1) & 0xFF
    return bytes(out[:size])
