"""Access widths of Game.exe's globals: every x86 memory operand of the code whose displacement is a global address
(plain or indexed); the widths the code uses for each address. The translator types the globals Ghidra left
untyped by these (an untyped global is a byte to Ghidra's printer, but the code reads it as int / short).

usage (capstone): python access_sizes.py <Game.exe> <decompile.c> <out access.txt>
out: "address width count scale" lines (scale: of the index register, 0 without one)
"""
import collections
import re
import struct
import sys

import capstone

exe, src, out = sys.argv[1:4]
d = open(exe, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
base = struct.unpack_from('<I', d, pe + 52)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + opt + 40 * i
    vs, va, rs, rp = struct.unpack_from('<IIII', d, o + 8)
    secs.append((base + va, rs, rp))


def code(addr, n):
    for va, rs, rp in secs:
        if va <= addr < va + rs:
            off = rp + addr - va
            return d[off:off + min(n, va + rs - addr)]
    return b''


starts = sorted(int(m.group(1), 16) for m in re.finditer(r'^// ===== \S+ @ ([0-9a-f]+)', open(src, encoding='utf-8').read(), re.M))
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True
widths = collections.defaultdict(collections.Counter)
for i, a in enumerate(starts):
    end = starts[i + 1] if i + 1 < len(starts) else a + 0x1000
    for ins in md.disasm(code(a, end - a), a):
        if ins.mnemonic.startswith('lea'):
            continue
        for op in ins.operands:
            if op.type != capstone.x86.X86_OP_MEM:
                continue
            disp = op.mem.disp & 0xffffffff
            if 0x401000 <= disp < 0x4000000:
                widths[disp][(op.size, op.mem.scale if op.mem.index else 0)] += 1
with open(out, 'w') as f:
    for a in sorted(widths):
        for (w, sc), n in sorted(widths[a].items()):
            f.write('%08x %d %d %d\n' % (a, w, n, sc))
print(len(widths), 'addresses')
