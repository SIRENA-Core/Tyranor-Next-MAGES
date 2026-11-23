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
# outside the phone module: the system menu (0x457b80 init, 0x457bc0 update of instruction 00:44, 0x4579e0 / 0x4571d0
# the draw of the system menu layer)
# globals Ghidra typed wrong (from the instructions that use them)
TYPE_FIXES = {0x016d78a8: (4, 'float'),
              # the CG viewer's zoom (0xde8f68, minimum 0xde8f70, saved copies +4) and scroll (0xde8f88 / 8c)
              0x00de8f68: (4, 'float'), 0x00de8f6c: (4, 'float'), 0x00de8f70: (4, 'float'),
              0x00de8f74: (4, 'float'), 0x00de8f88: (4, 'float'), 0x00de8f8c: (4, 'float'),  # the pulse of the config cursor (+= 0.05, compared with 1.0 / 2.0)
              0x02efc1cc: (4, 'undefined4'),
              0x016d78b0: (4, 'int'),  # the config row in focus (-1: none)
              0x016d8220: (4, 'int'),
              0x016dc0d8: (4, 'int'),  # TIPS: the entries of the lists
              0x016dc108: (4, 'int'), 0x016dc0ec: (4, 'int'), 0x005c9734: (4, 'int'),
              0x032fc808: (4, 'int'),
              0x016dc0f8: (4, 'int'), 0x016dc0fc: (4, 'int'),
              0x017714d8: (2, 'short'),
              # TIPS: the table (6 ints per tip; 0x16d8fac is read through byte offsets), the list counts and entries
              0x016d8f98: (4, 'int'), 0x016d8f9c: (4, 'int'), 0x016d8fa0: (4, 'int'), 0x016d8fa4: (4, 'int'),
              0x016d8fa8: (4, 'int'), 0x016dae10: (4, 'int'), 0x016dae14: (4, 'int'), 0x016dae18: (4, 'int')}  # the glyphs of the text layout (codes and 0x8000 + control codes)  # TIPS: the text scroll  # the mouse moved since the button went down (y)  # the config rows' fade (int per row)
# the text layout's pointers into the text (ruby start 0x17816bc, the ruby bases 0x178ec90)
POINTER_GLOBALS = (0x017816bc, 0x0178ec90)
# ... with the type Ghidra gave them (also used as a flag: Sg0Emu::PtrVar)
TYPED_POINTER_GLOBALS = {0x00de8fec: 'int', 0x00de8ff0: 'int'}  # the album's entries (CG library)
EXTRA_FUNCS = {0x4571d0, 0x4579e0, 0x457b80, 0x457bc0,
               # the save / load menu (instruction 10:23: 0x455f90 init, 0x456030 update; 0x454f80 draw), its header
               # with the turning ornament (0x456940), number and ASCII text helpers
               0x454e00, 0x454ee0, 0x454f50, 0x454f80, 0x455ef0, 0x455f90, 0x456030, 0x456940,
               0x4648d0, 0x48b6b0, 0x45d5c0, 0x460c40, 0x463b20,
               # the config screen (instruction 10:13: 0x453620 init, 0x453d70 update, 0x4524f0, 0x4527b0 defaults;
               # 0x452910 draw)
               0x4524a0, 0x4524f0, 0x452500, 0x452790, 0x4527b0, 0x452910, 0x452c00, 0x452e10, 0x4530b0, 0x4533a0,
               0x4535e0, 0x453620, 0x453700, 0x453d70, 0x42e750,
               # the backlog screen under the engine backlog (0x451fe0, case 1 of 0x4579e0)
               0x451fe0,
               # the system message box (instruction 00:43 in sysmenu.cpp): 0x457dc0 keeps / restores its state
               0x457dc0,
               # the clear list (instruction 10:21: 0x451000; 0x4504c0 draw; 0x42a410 the CG count)
               0x451000, 0x4504c0, 0x42a410, 0x42a4f0,
               # the CG / sound / movie libraries (instructions 10:1F 0x42c530 0x42c630 0x42e2b0, 10:1D 0x42d220
               # 0x42d3c0, 10:20 0x42cda0 0x42ce10; drawn by 0x42c830, 0x42d770, 0x42bf10) and their helpers
               0x42a650, 0x42ae40, 0x42b260, 0x42b500, 0x42bae0, 0x42bbe0, 0x42bdf0, 0x42c530, 0x42c630, 0x42c830,
               0x42cda0, 0x42ce10, 0x42d0b0, 0x42d220, 0x42d3c0, 0x42e040, 0x42e2b0, 0x42e390, 0x42e700, 0x42bf10,
               0x42d770, 0x42a3e0, 0x42a7d0, 0x42dc30, 0x42b330, 0x42bc70,
               # the TIPS screen (instruction 10:33: 0x458cb0 table, 0x459a90 init, 0x459eb0 update, 0x45a9b0; 0x458d30
               # draw) and the text layout of its text (0x45dcb0: 0x4673e0 layout, 0x465f00 lines, 0x45dfc0 draw)
               0x458200, 0x458670, 0x458780, 0x4587c0, 0x4589b0, 0x4589f0, 0x458a30, 0x458b60, 0x458bb0, 0x458c50,
               0x458cb0, 0x458d30, 0x459a90, 0x459eb0, 0x45a880, 0x45a970, 0x45a9b0, 0x45aae0, 0x45ac90,
               0x45dcb0, 0x45dfc0, 0x45e2b0, 0x465f00, 0x4673e0, 0x467cd0, 0x467e30, 0x466800, 0x42ffc0}

text = open(src, encoding='utf-8').read()
funcs = []
handported = []  # their globals go into the header too
for f in re.split(r'(?=^// ===== )', text, flags=re.M):
    m = re.match(r'// ===== \S+ @ ([0-9a-f]+)', f)
    if not m:
        continue
    a = int(m.group(1), 16)
    if a in EXTRA_FUNCS:
        funcs.append((a, f))
        continue
    if a >= 0x478000:
        continue  # past the phone module (the input can be the whole decompile)
    if a >= 0x46b600 and a not in skip:
        funcs.append((a, f))
    elif a in skip and a < 0x4773b0:
        handported.append(f)

types = {}
# the widths the x86 code accesses each global with (access_sizes.py; access.txt beside data.txt)
import collections  # noqa: E402
import os  # noqa: E402
widths = collections.defaultdict(collections.Counter)
scales = collections.defaultdict(set)  # the index scales of the accesses (0: none)
_acc = os.path.join(os.path.dirname(datatxt), 'access.txt')
if os.path.exists(_acc):
    for line in open(_acc):
        a_, w_, n_, sc_ = line.split()
        if int(w_) in (1, 2, 4, 8):
            widths[int(a_, 16)][int(w_)] += int(n_)
            if int(sc_):
                scales[int(a_, 16)].add(int(sc_))
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
        f = re.sub(r'\((?:int|uint)\)\s*\(%s\b' % n, '(intptr_t)(%s' % n, f)
    return re.sub(r'\((?:int|uint)\)\s*&', '(intptr_t)&', f)


COLORS = {0x00dcc95a, 0x00e41616, 0x005ade1f, 0x00808080, 0x00cce048, 0x00888888, 0x00ca0000, 0x00ff8a00, 0x00666666, 0x01010101, 0x00777777, 0x00ff3d00}
body = ''.join(widen_pointer_casts(f) for _, f in funcs)
# colours mistaken for addresses
for c in COLORS:
    body = body.replace('&DAT_%08x' % c, '0x%x' % c)
    body = re.sub(r'\b(\w+) = 0x%x;' % c, lambda m: '%s = (std::remove_reference_t<decltype(%s)>)0x%x;' % (m.group(1), m.group(1), c), body)
body = re.sub(r'\n\s*__security_check_cookie\([^;]*\);', '', body)
body = re.sub(r'\n\s*local_\w+ = (?:\(\w+\))?\(?DAT_00dde17c \^[^;]*;', '', body)
body = re.sub(r'\n\s*__alloca_probe\(\);', '', body)
body = body.replace('__fastcall ', '').replace('__thiscall ', '')
# Ghidra's sub-piece of a wider value
body = re.sub(r'\b(\w+)\._4_4_', r'(uint32_t)((uint64_t)(\1) >> 32)', body)
body = re.sub(r'\b(\w+)\._0_4_', r'(uint32_t)(\1)', body)
# 0x42fb00 on a pseudo thread whose instruction pointer is a local after its buffer (local_c / local_20 = p + 1;
# eval; p = local_c): an expression of a script string (a colour tag)
body = re.sub(r'(\w+) = (\w+) \+ 1;\n(\s*)FUN_0042fb00\(\w+,(&?\w+)\);\n\s*\2 = \1;',
              r'\2 = (decltype(\2))Sg0Emu::EvalAt(\2 + 1, (void *)\4);', body)
# char is unsigned on ARM: Ghidra's char is the signed char of x86 (tests like (char)b < '\0' for the glyph flag)
body = body.replace('(char)', '(signed char)')
body = re.sub(r'^(\s+)char (\*?)(cVar|pcVar|local_)', r'\1signed char \2\3', body, flags=re.M)
body = body.replace('(char *)', '(signed char *)')
# string literals of rdata (s_text_005cb1b0): the table at that address
body = re.sub(r'\bs_\w*?_(00[45][0-9a-f]{5})\b', r'(&DAT_\1)', body)
# globals of the original that hold pointers (32 bit there): kept beside emulated memory (Sg0Emu::PtrSlot)
for a, ty in TYPED_POINTER_GLOBALS.items():
    body = re.sub(r'\bDAT_%08x\b' % a, '(*Sg0Emu::TypedSlot<%s>(0x%08x))' % (ty, a), body)
for a in POINTER_GLOBALS:
    body = body.replace('(&DAT_%08x)[' % a, 'Sg0Emu::PtrSlot(0x%08x)[' % a)
    body = re.sub(r'\bDAT_%08x\b' % a, '(*Sg0Emu::PtrSlot(0x%08x))' % a, body)


def handle_ptrs(body):
    """(T *)FUN_0047f1f0(...) / (T *)FUN_004645a0(...): the address of a script string in the original, its handle
    here (the text through Sg0Emu::HandlePtr)"""
    out, i = [], 0
    for m in re.finditer(r'\((?:signed )?\w+ \*\)(FUN_0047f1f0|FUN_004645a0)\(', body):
        if m.start() < i:
            continue
        j, depth = m.end(), 1
        while depth:
            depth += {'(': 1, ')': -1}.get(body[j], 0)
            j += 1
        cast = body[m.start():m.start(1)]
        out.append(body[i:m.start()] + cast + 'Sg0Emu::HandlePtr(' + body[m.start(1):j] + ')')
        i = j
    return ''.join(out) + body[i:]


body = handle_ptrs(body)
sys.path.insert(0, __import__('os').path.dirname(__file__))
import phone_fixes  # noqa: E402
body = phone_fixes.apply(body)

# address literals: *(int *)(i * 4 + 0x5cb618) reads emulated memory too
EMULATED = [(0x401000, 0x600000), (0xdc0000, 0xe50000), (0x16d0000, 0x16e0000), (0x1770000, 0x1800000), (0x1850000, 0x1860000), (0x18e0000, 0x18f0000), (0x1970000, 0x19b0000), (0x2ed0000, 0x2ef0000), (0x2efc000, 0x2efd000),
            (0x32f0000, 0x3300000)]
literal_addrs = []


def address_literal(m):
    v = int(m.group(3), 16)
    if not any(a <= v < b for a, b in EMULATED):
        return m.group(0)
    literal_addrs.append(v)
    return '*(%s *)((intptr_t)(%s) + (intptr_t)Sg0Emu::At(0x%08x))' % (m.group(1), m.group(2), v)


body = re.sub(r'\*\((\w+) \*\)\(([^()]*?) \+ 0x([0-9a-f]{6,8})\)', address_literal, body)

syms = sorted(set(re.findall(r'\b((?:_?DAT|uRam|PTR_DAT|_?UNK)_?([0-9a-f]{8}))\b', body + ''.join(handported))))
RDATA = (0x00401000, 0x00600000)

macro_lines = []
rdata_ranges = []
for name, hexa in syms:
    a = int(hexa, 16)
    if a in (0x02ee7660, 0x02ee7188, 0x02ee71a4):
        continue  # ScrWork, the TIPS bits (phoneemu.h)
    if 0x02ee7120 <= a < 0x02ee7184 and not name.startswith('_'):
        # the BGM flags (a byte per track, 100): the engine save system's (MO6TWPC::SaveSystem::BgmBytes)
        macro_lines.append('#define %s (PhoneCode::BgmBytes()[0x%x])' % (name, a - 0x02ee7120))
        continue
    size, ty = types.get(a, (1, 'undefined'))
    if a not in types and a in widths and name.startswith('DAT') and re.search(r'(?<![&\w])%s\b|\(&%s\)\[' % (name, name), body):
        # untyped (a byte to Ghidra's printer): the width the code reads it with (access.txt); only where the
        # decompile indexes it or uses it plainly (&DAT_x + n is a byte offset)
        size = widths[a].most_common(1)[0][0]
        ty = {4: 'undefined4', 2: 'undefined2', 8: 'undefined8'}.get(size, 'undefined')
    elif a not in types and len(scales.get(a, ())) == 1:
        # only &DAT_x + i * K: in units of the type Ghidra gave it, which the x86 index scale S tells (S / K)
        ks = {int(k, 0) for k in re.findall(r'&%s \+ [\w\[\]]+ \* (0x[0-9a-f]+|\d+)\)' % name, body)}
        sc = next(iter(scales[a]))
        if len(ks) == 1 and sc > next(iter(ks)) and sc % next(iter(ks)) == 0:
            size = sc // next(iter(ks))
            ty = {2: 'undefined2', 4: 'undefined4', 8: 'undefined8'}.get(size, 'undefined')
    if a in TYPE_FIXES:
        size, ty = TYPE_FIXES[a]
    if (name.startswith('_') or name.startswith('uRam')) and size < 4:
        size, ty = 4, 'undefined4'  # Ghidra's '_DAT': accessed wider than the data it defined there (4 bytes)
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
        ct = 'int16_t' if ty == 'short' else 'uint16_t'
    else:
        ct = 'uint8_t'
    if RDATA[0] <= a < RDATA[1]:
        rdata_ranges.append(a)
    if name.startswith('PTR_DAT'):
        ct = 'Sg0Emu::EmuPtr'  # an address of emulated memory
    macro_lines.append('#define %s (*reinterpret_cast<%s*>(Sg0Emu::At(0x%08x)))' % (name, ct, a))

# rdata: copy the tables after every referenced rdata symbol; merged into 16 byte windows. The shims read some
# tables too: glyph widths 0x5c9b58 / 0x5cb250, the line break glyphs 0x5cb108, the text colours 0x5cb3e0 (64 pairs).
EXTRA = {0x005c9b58: 0x160, 0x005cb108: 0x28, 0x005cb250: 0x160, 0x005cb3e0: 0x200}
rdata_ranges += [a for a in literal_addrs if RDATA[0] <= a < RDATA[1]]
# a table ends where Ghidra put the next label (the next address the code refers to), at most 0x400 bytes on
labels = sorted(a for a in types if RDATA[0] <= a < RDATA[1])
import bisect  # noqa: E402


def extent(a):
    """a table ends at the next label Ghidra put after it; byte tables are labelled byte by byte, so labels that
    only follow the previous one by a byte do not end it; at most 0x400 bytes"""
    if a in EXTRA:
        return EXTRA[a]
    i = bisect.bisect_right(labels, a)
    end, prev = a + 0x400, a
    while i < len(labels) and labels[i] < end:
        if labels[i] - prev > 1 or labels[i] in referenced:
            end = labels[i]
            break
        prev = labels[i]
        i += 1
    return max(end - a, types.get(a, (4, ''))[0], 4)


referenced = set(rdata_ranges)
win = {}
for a in list(rdata_ranges) + list(EXTRA):
    for o in range(a - (a % 16), a + extent(a), 16):
        win.setdefault(o, exe_bytes(o, 16))
rdata_lines = []
for o in sorted(win):
    rdata_lines.append('    {0x%08x, {%s}},' % (o, ','.join('0x%02x' % b for b in win[o])))

# Calls of the translated helpers outside the phone module (text, numbers) pass char buffers where Ghidra typed the
# parameter as uint * and the like: each argument goes through Cv (phoneemu.h), which converts to the parameter type.
def wrap_calls(text, targets):
    out = []
    i = 0
    pat = re.compile(r'\b(FUN_00(%s))\(' % '|'.join('%06x' % t for t in targets))
    while True:
        m = pat.search(text, i)
        if not m:
            out.append(text[i:])
            return ''.join(out)
        line_start = text.rfind('\n', 0, m.start()) + 1
        if text[line_start] not in ' 	':
            out.append(text[i:m.end()])  # a definition
            i = m.end()
            continue
        j = m.end()
        depth, args, cur = 1, [], ''
        while depth:
            c = text[j]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
            if c == ',' and depth == 1:
                args.append(cur)
                cur = ''
            else:
                cur += c
            j += 1
        args.append(cur)
        args = [wrap_calls(a, targets) for a in args]
        n = arity.get(int(m.group(2), 16))
        if n is not None and len(args) > n:
            args = args[:n]  # stack junk Ghidra took for arguments
        real = [a for a in args if a.strip()]
        if n is not None and len(real) < n:
            args = real + ['0'] * (n - len(real))  # a parameter Ghidra saw that this caller did not set: whatever
        out.append(text[i:m.end()] + ','.join('Cv(%s)' % a.strip() if a.strip() else a for a in args) + ')')
        i = j + 1


arity = {}
for a, _ in funcs:
    m = re.search(r'^\w[^\n(]*FUN_00%06x\(([^)]*)\)' % a, body, re.M)
    if m:
        arity[a] = 0 if m.group(1).strip() in ('', 'void') else m.group(1).count(',') + 1
body = wrap_calls(body, [a for a in EXTRA_FUNCS if a not in (0x4571d0, 0x4579e0, 0x457b80, 0x457bc0)])

# signatures for forward declarations
decls = []
for a, _ in funcs:
    m = re.search(r'^\s*\n(\w[^\n]*FUN_00%06x\([^)]*\))\s*\n' % a, body, re.M)
    if m:
        decls.append(m.group(1).replace('__fastcall ', '').replace('__thiscall ', '') + ';')

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
