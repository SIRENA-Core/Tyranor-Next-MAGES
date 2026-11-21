"""Merge the system data of a STEINS;GATE Steam SAVEDATA.DAT (read marks, CG/BGM/tips unlocks, clear flags, system
variables) into the engine's sg-pc SYSTEM.DAT ("MO6S" format of src/games/mo6twpc/savesystem.cpp). Save slots and
settings of the engine file are kept.

Usage: python -I import_steam_save.py <SAVEDATA.DAT> <Game.exe> <SYSTEM.DAT in> <SYSTEM.DAT out>

Steam layout (Game.exe 0x45cf90/0x45e2xx): file = syssave (0x3820 bytes) + fsave + msave (0x3b97c0 each).
syssave: +0x80 FlagWork bytes 100..149, +0xb2 FlagWork bytes 460..499, +0xdc ScrWork 1600..1999, +0x71c ScrWork
2000..2099, +0xc16 CG flags (1200 bits, LSB first), +0xcac BGM flags (100 bytes), +0xd10 read marks (10000 bytes,
bit = table[script].start + line, table of (count, start) u32 pairs at VA 0x52c9d8), +0x3420 extra data (0x400).
"""
import struct
import sys
import zlib

SYS_SIZE = 0x3820


def exe_reader(exe):
    pe = struct.unpack_from('<I', exe, 0x3c)[0]
    nsec = struct.unpack_from('<H', exe, pe + 6)[0]
    opt = struct.unpack_from('<H', exe, pe + 20)[0]
    base = struct.unpack_from('<I', exe, pe + 24 + 28)[0]
    secs = []
    for i in range(nsec):
        o = pe + 24 + opt + 40 * i
        vs, va, rs, ra = struct.unpack_from('<IIII', exe, o + 8)
        secs.append((va, max(vs, rs), ra))

    def read(vaddr, n):
        rva = vaddr - base
        for va, size, ra in secs:
            if va <= rva < va + size:
                return exe[ra + rva - va:ra + rva - va + n]
        raise ValueError(hex(vaddr))
    return read


def read_marks(sysblk, exe):
    rd = exe_reader(exe)
    marks = sysblk[0xd10:0xd10 + 10000]
    table = rd(0x52c9d8, 8 * 512)
    lines = set()
    for sid in range(512):
        count, start = struct.unpack_from('<II', table, 8 * sid)
        if count == 0 or count > 0xffff or start + count > 80000:
            continue
        for line in range(count):
            b = start + line
            if marks[b >> 3] & (1 << (b & 7)):
                lines.add((sid << 16) | line)
    return lines


class R:
    def __init__(self, d, p=0):
        self.d, self.p = d, p

    def raw(self, n):
        v = self.d[self.p:self.p + n]
        assert len(v) == n, 'truncated'
        self.p += n
        return v

    def u32(self):
        return struct.unpack('<I', self.raw(4))[0]


def main():
    steam_path, exe_path, in_path, out_path = sys.argv[1:5]
    steam = open(steam_path, 'rb').read()
    exe = open(exe_path, 'rb').read()
    assert len(steam) == SYS_SIZE + 2 * 0x3b97c0, 'not a STEINS;GATE Steam SAVEDATA.DAT'
    s = steam[:SYS_SIZE]

    data = open(in_path, 'rb').read()
    assert data[:4] == b'MO6S'
    assert zlib.crc32(data[:-4]) == struct.unpack('<I', data[-4:])[0], 'engine save CRC mismatch'
    r = R(data, 4)
    version = r.u32()
    sys_size = r.u32()
    blob_start = r.p
    blob = bytearray(r.raw(sys_size))
    rest = data[r.p:-4]

    # parse the engine system blob (SaveSystem::SaveSystemData)
    b = R(blob)
    off_flags1 = b.p; b.raw(50)
    off_flags2 = b.p; b.raw(40)
    off_scr = b.p; b.raw(500 * 4)
    b.raw(8 + 8)
    groups = b.u32(); b.raw(4 * groups)
    b.raw(33 + 33 * 4)
    b.raw(48)
    off_ev = b.p; b.raw(1200)
    off_bgm = b.p; b.raw(200)
    off_extra = b.p; b.raw(1024)
    off_lines = b.p
    n = b.u32()
    lines = set(struct.unpack_from(f'<{n}I', blob, b.p))
    assert b.p + 4 * n == len(blob), 'unexpected system blob layout'

    def merge_or(off, src):
        for i, v in enumerate(src):
            blob[off + i] |= v

    merge_or(off_flags1, s[0x80:0x80 + 50])
    merge_or(off_flags2, s[0xb2:0xb2 + 40])
    # system ScrWork: take the cleared game's values (play time, clear counts, ...)
    scr = list(struct.unpack_from('<500i', blob, off_scr))
    steam_scr = list(struct.unpack_from('<400i', s, 0xdc)) + list(struct.unpack_from('<100i', s, 0x71c))
    for i, v in enumerate(steam_scr):
        if v:
            scr[i] = v
    struct.pack_into('<500i', blob, off_scr, *scr)
    ev = s[0xc16:0xc16 + 150]
    for i in range(1200):
        if ev[i >> 3] & (1 << (i & 7)):
            blob[off_ev + i] = 1
    merge_or(off_bgm, s[0xcac:0xcac + 100])
    merge_or(off_extra, s[0x3420:0x3420 + 0x400])
    imported = read_marks(s, exe)
    before = len(lines)
    lines |= imported
    blob = bytes(blob[:off_lines]) + struct.pack('<I', len(lines)) + struct.pack(f'<{len(lines)}I', *sorted(lines))

    out = data[:blob_start - 4] + struct.pack('<I', len(blob)) + blob + rest
    out += struct.pack('<I', zlib.crc32(out))
    open(out_path, 'wb').write(out)
    print(f'version {version}: read lines {before} -> {len(lines)} ({len(imported)} from Steam), '
          f'CG flags {sum(blob[off_ev:off_ev + 1200])}, wrote {out_path}')


if __name__ == '__main__':
    main()
