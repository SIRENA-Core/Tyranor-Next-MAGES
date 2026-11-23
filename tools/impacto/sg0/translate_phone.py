"""Translate the S;G0 phone module (Game.exe 0x46b600..0x478000) of a Ghidra decompile into C++ for the engine.

usage: python translate_phone.py <decompile.c> <data.txt> <Game.exe> <out dir>/phonecode.cpp $(cat phone_skip.txt)

decompile.c: every function of Game.exe, "// ===== FUN_x @ addr" before each (ghidra/DumpRange.java over
0x401000..0x549000); data.txt: the data types Ghidra gave the globals (ghidra/DumpData.java). Writes phonecode.cpp
and phoneglobals.h (src/games/sg0 of the patch tree). The skipped functions are hand ported (phonerine.cpp) or not
part of the phone (save file io, achievements).

The globals of the original are kept at their addresses in emulated memory (Sg0Emu::At(address)), so the decompiled
expressions (interleaved tables indexed like (&DAT_0197afe4)[i * 5]) keep their meaning. Read only tables of the
original (rdata) are copied from Game.exe into the generated file. External functions keep their FUN_00xxxxxx names
and are implemented in phoneshim.cpp.
"""
import re
import struct
import sys

src, datatxt, exe, out = sys.argv[1:5]
skip = {int(a, 16) for a in sys.argv[5:]}

text = open(src, encoding='utf-8').read()
funcs = []
handported = []  # their globals go into the header too
for f in re.split(r'(?=^// ===== )', text, flags=re.M):
    m = re.match(r'// ===== \S+ @ ([0-9a-f]+)', f)
    if not m:
        continue
    a = int(m.group(1), 16)
    if a >= 0x478000:
        continue  # past the phone module (the input can be the whole decompile)
    if a >= 0x46b600 and a not in skip:
        funcs.append((a, f))
    elif a in skip and a < 0x4773b0:
        handported.append(f)

types = {}
for line in open(datatxt, encoding='utf-8'):
    p = line.split(None, 2)
    if len(p) == 3:
        types[int(p[0], 16)] = (int(p[1]), p[2].strip())

d = open(exe, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
base = struct.unpack_from('<I', d, pe + 52)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + opt + 40 * i
    vs, va, rs, rp = struct.unpack_from('<IIII', d, o + 8)
    secs.append((base + va, max(vs, rs), rs, rp))


def exe_bytes(addr, n):
    for va, size, rs, rp in secs:
        if va <= addr < va + size:
            off = addr - va
            raw = d[rp + off: rp + min(off + n, rs)]
            return raw + b'\0' * (n - len(raw))
    raise ValueError(hex(addr))


def widen_pointer_casts(f):
    # Ghidra does address arithmetic on 32 bit ints, (int)local_3a8 + n; pointers are 64 bit here
    ptrs = set(re.findall(r'^\s+[\w ]+\*\s*(\w+)\s*(?:\[[^\]]*\])?;', f, re.M))
    ptrs |= set(re.findall(r'^\s+[\w ]+?\s(\w+)\s*\[[^\]]*\];', f, re.M))
    sig = re.search(r'^\w[^(\n]*FUN_\w+\(([^)]*)\)', f, re.M)  # pointer parameters (may span lines)
    if sig:
        ptrs |= set(re.findall(r'\*\s*(\w+)\s*(?:,|$)', sig.group(1)))
    for n in ptrs:
        f = re.sub(r'\((?:int|uint)\)\s*%s\b' % n, '(intptr_t)%s' % n, f)
    return re.sub(r'\((?:int|uint)\)\s*&', '(intptr_t)&', f)


COLORS = {0x00dcc95a, 0x00e41616, 0x005ade1f, 0x00808080, 0x00cce048}
body = ''.join(widen_pointer_casts(f) for _, f in funcs)
# colours mistaken for addresses
for c in COLORS:
    body = body.replace('&DAT_%08x' % c, '0x%x' % c)
    body = re.sub(r'\bpuVar(\d+) = 0x%x;' % c, lambda m: 'puVar%s = (undefined1 *)0x%x;' % (m.group(1), c), body)
body = re.sub(r'\n\s*__security_check_cookie\([^;]*\);', '', body)
body = re.sub(r'\n\s*local_\w+ = (?:\(\w+\))?\(?DAT_00dde17c \^[^;]*;', '', body)
body = re.sub(r'\n\s*__alloca_probe\(\);', '', body)
body = body.replace('__fastcall ', '')
sys.path.insert(0, __import__('os').path.dirname(__file__))
import phone_fixes  # noqa: E402
body = phone_fixes.apply(body)

# address literals: *(int *)(i * 4 + 0x5cb618) reads emulated memory too
EMULATED = [(0x401000, 0x600000), (0xdc0000, 0xe50000), (0x1970000, 0x19b0000), (0x2ed0000, 0x2ef0000),
            (0x32f0000, 0x3300000)]
literal_addrs = []


def address_literal(m):
    v = int(m.group(3), 16)
    if not any(a <= v < b for a, b in EMULATED):
        return m.group(0)
    literal_addrs.append(v)
    return '*(%s *)((intptr_t)(%s) + (intptr_t)Sg0Emu::At(0x%08x))' % (m.group(1), m.group(2), v)


body = re.sub(r'\*\((\w+) \*\)\(([^()]*?) \+ 0x([0-9a-f]{6,8})\)', address_literal, body)

syms = sorted(set(re.findall(r'\b((?:_?DAT|uRam|PTR_DAT)_?([0-9a-f]{8}))\b', body + ''.join(handported))))
RDATA = (0x00401000, 0x00600000)

macro_lines = []
rdata_ranges = []
for name, hexa in syms:
    a = int(hexa, 16)
    if a == 0x02ee7660:
        continue  # ScrWork (phoneemu.h)
    size, ty = types.get(a, (1, 'undefined'))
    if 'double' in ty or size == 8:
        ct = 'double' if a == 0x005ba790 else 'uint64_t'
    elif size == 4:
        # undefined4: signed (Ghidra prints (float)(DAT_x + -0x66) for signed conversions, unsigned ones as the 0x5ba790 idiom)
        ct = 'float' if ty == 'float' else ('uint32_t' if ty in ('uint', 'dword') else 'int32_t')
        if ty.endswith('*') or 'pointer' in ty:
            ct = 'uint32_t'
        if RDATA[0] <= a < RDATA[1] and ct in ('uint32_t', 'int32_t') and not ty.endswith('*'):
            # Ghidra leaves float constants untyped: a sane float bit pattern that is not a small integer is a float
            v = struct.unpack('<I', exe_bytes(a, 4))[0]
            f = struct.unpack('<f', exe_bytes(a, 4))[0]
            if v > 0xffff and 1e-6 < abs(f) < 1e7:
                ct = 'float'
    elif size == 2:
        ct = 'uint16_t'
    else:
        ct = 'uint8_t'
    if RDATA[0] <= a < RDATA[1]:
        rdata_ranges.append(a)
    macro_lines.append('#define %s (*reinterpret_cast<%s*>(Sg0Emu::At(0x%08x)))' % (name, ct, a))

# rdata: copy the tables after every referenced rdata symbol; merged into 16 byte windows. The shims read some
# tables too: glyph widths 0x5c9b58 / 0x5cb250, the line break glyphs 0x5cb108, the text colours 0x5cb3e0.
EXTRA = {0x005c9b58: 0x160, 0x005cb108: 0x28, 0x005cb250: 0x160, 0x005cb3e0: 0x80}
rdata_ranges += [a for a in literal_addrs if RDATA[0] <= a < RDATA[1]]
# a table ends where Ghidra put the next label (the next address the code refers to), at most 0x400 bytes on
labels = sorted(a for a in types if RDATA[0] <= a < RDATA[1])
import bisect  # noqa: E402


def extent(a):
    if a in EXTRA:
        return EXTRA[a]
    i = bisect.bisect_right(labels, a)
    nxt = labels[i] if i < len(labels) else a + 0x400
    return max(min(nxt - a, 0x400), types.get(a, (4, ''))[0], 4)


win = {}
for a in list(rdata_ranges) + list(EXTRA):
    for o in range(a - (a % 16), a + extent(a), 16):
        win.setdefault(o, exe_bytes(o, 16))
rdata_lines = []
for o in sorted(win):
    rdata_lines.append('    {0x%08x, {%s}},' % (o, ','.join('0x%02x' % b for b in win[o])))

# signatures for forward declarations
decls = []
for a, _ in funcs:
    m = re.search(r'^\s*\n(\w[^\n]*FUN_00%06x\([^)]*\))\s*\n' % a, body, re.M)
    if m:
        decls.append(m.group(1).replace('__fastcall ', '') + ';')

hdr = '''// Generated by tools/impacto/sg0/translate_phone.py from the Ghidra decompile of the STEINS;GATE 0 (Steam) Game.exe,
// phone module 0x46b600..0x478000. Do not edit by hand; regenerate and patch the listed hand ported functions instead.
#include "phoneemu.h"

// decompiled code: Ghidra's precedence parentheses, signedness and int / pointer conversions are kept as they are
#pragma clang diagnostic ignored "-Wshift-op-parentheses"
#pragma clang diagnostic ignored "-Wsign-compare"
#pragma clang diagnostic ignored "-Wint-to-pointer-cast"
#pragma clang diagnostic ignored "-Wparentheses"
#pragma clang diagnostic ignored "-Wpointer-sign"
#pragma clang diagnostic ignored "-Wunused-variable"
#pragma clang diagnostic ignored "-Wunused-but-set-variable"
#pragma clang diagnostic ignored "-Wunused-label"
#pragma clang diagnostic ignored "-Wsometimes-uninitialized"

namespace Impacto {
namespace SG0 {
namespace PhoneCode {
using namespace Sg0Emu::Types;

'''
GLOBALS_HDR = """#pragma once
// Generated by tools/impacto/sg0/translate_phone.py: the globals of the S;G0 phone at their Game.exe addresses
// (emulated memory, phoneemu.h) and the declarations of the translated functions.
#include "phoneemu.h"

"""
with open(out, 'w', encoding='utf-8', newline='\n') as fo:
    fo.write(hdr.replace('#include "phoneemu.h"', '#include "phoneglobals.h"'))
    fo.write('const Sg0Emu::RdataChunk RdataChunks[] = {\n' + '\n'.join(rdata_lines) + '\n};\n')
    fo.write('const size_t RdataChunkCount = sizeof(RdataChunks) / sizeof(RdataChunks[0]);\n\n')
    fo.write(body)
    fo.write('\n}  // namespace PhoneCode\n}  // namespace SG0\n}  // namespace Impacto\n')
with open(__import__('os').path.join(__import__('os').path.dirname(out) or '.', 'phoneglobals.h'), 'w', encoding='utf-8', newline='\n') as fh:
    fh.write(GLOBALS_HDR + '\n'.join(macro_lines) + '\n\nnamespace Impacto {\nnamespace SG0 {\nnamespace PhoneCode {\n'
             + 'using namespace Sg0Emu::Types;\n' + '\n'.join(decls)
             + '\n}  // namespace PhoneCode\n}  // namespace SG0\n}  // namespace Impacto\n')
print('functions', len(funcs), 'symbols', len(syms), 'rdata chunks', len(rdata_lines))
