"""Exact text fixes applied to the decompiled phone code before it is written (translate_phone.py)."""
import re

FIXES = [
    # 0x470110: the label table entry is read through the script pointer (labels are buffer offsets here)
    ('puVar1 = (ushort *)FUN_0047f170(DAT_0197afd0,param_1);', 'puVar1 = (ushort *)Sg0Emu::LabelPtr(DAT_0197afd0,param_1);'),
    # 0x475650: Ghidra reuses param_1 for the y position (int) and for the sticker pointer
    ('void FUN_00475650(int *param_1,uint param_2)', 'void FUN_00475650(int param_1y,uint param_2)'),
    ('  if (((intptr_t)param_1 + 0x1e < 0x319) && (-1 < (intptr_t)param_1 + 0x1e + (&DAT_0197c054)[iVar3])) {',
     '  int *param_1;\n  if ((param_1y + 0x1e < 0x319) && (-1 < param_1y + 0x1e + (int)(&DAT_0197c054)[iVar3])) {'),
    ('    iVar3 = (intptr_t)param_1 + 0x66 + (&DAT_0197c054)[iVar3];',
     '    iVar3 = param_1y + 0x66 + (&DAT_0197c054)[iVar3];'),
    ('      param_1 = &DAT_0197c060 + iVar2 * 0x1d;', '      param_1 = (int *)(&DAT_0197c060 + iVar2 * 0x1d);'),
    # the phone state of a save: a buffer pointer (32 bit in the original)
    ('void FUN_00470620(undefined4 param_1,undefined4 *param_2)', 'void FUN_00470620(uint8_t *param_1,undefined4 *param_2)'),
    ('void FUN_00475ed0(undefined4 param_1,undefined4 *param_2)', 'void FUN_00475ed0(uint8_t *param_1,undefined4 *param_2)'),
]


def blob_locals(body, addr):
    """0x470620 / 0x475ed0 pack / unpack the phone state (0x3ee0 bytes of a save) through one local struct that
    Ghidra split into separate locals; put them back into one buffer: local_X is at offset 0x3edc - X."""
    m = re.search(r'(// ===== FUN_00%06x @ [0-9a-f]+\n.*?)(?=// ===== |\Z)' % addr, body, re.S)
    f = m.group(1)
    decl = re.compile(r'^  (byte|ushort|undefined2|undefined4|undefined1|int|uint) (local_([0-9a-f]+))( \[(\d+)\])?;\n', re.M)
    names = []
    for d in decl.finditer(f):
        ty, name, off, arr, n = d.groups()
        o = 0x3edc - int(off, 16)
        if o < 0 or o >= 0x3edc + 4 or int(off, 16) < 0xc:
            continue
        names.append((ty, name, o, n))
    for ty, name, o, n in names:
        f = re.sub(r'^  [\w]+ %s( \[\d+\])?;\n' % name, '', f, flags=re.M)
    defs = ''.join(
        '#define %s (%s)\n' % (name, ('reinterpret_cast<%s*>(Blob + 0x%x)' % (ty, o)) if n else
                                     ('*reinterpret_cast<%s*>(Blob + 0x%x)' % (ty, o)))
        for ty, name, o, n in names)
    undefs = ''.join('#undef %s\n' % name for _, name, _, _ in names)
    f = f.replace('\n{\n', '\n{\n  alignas(4) uint8_t Blob[0x3ee0] = {};\n', 1)
    return body.replace(m.group(1), defs + f + undefs)


def scrwork_locals(body):
    """iVar3 = DAT_02ee7660; ... *(uint *)(iVar3 + 0x1f68): the ScrWork base is a 64 bit pointer here, so a local
    that holds it becomes intptr_t."""
    out = []
    for f in re.split(r'(?=^// ===== )', body, flags=re.M):
        for v in set(re.findall(r'\b([iu]Var\d+) = DAT_02ee7660;', f)):
            f = re.sub(r'^(\s+)(?:int|uint|undefined4) %s;' % v, r'\1intptr_t %s;' % v, f, count=1, flags=re.M)
        out.append(f)
    return ''.join(out)


def apply(body):
    body = scrwork_locals(body)
    body = blob_locals(body, 0x470620)
    body = blob_locals(body, 0x475ed0)
    for old, new in FIXES:
        if old not in body:
            raise SystemExit('fix not found: ' + old[:70])
        body = body.replace(old, new)
    # pointer = &DAT_...: the emulated globals have one signedness, the pointers of the decompile another
    body = re.sub(r'\b(p[a-z]Var\d+|local_\w+) = (&_?DAT_\w+(?: [+-] [^;]+)?);', r'\1 = (decltype(\1))(\2);', body)
    return body
