"""Exact text fixes applied to the decompiled phone code before it is written (translate_phone.py)."""
import re

FIXES = [
    # 0x42b260: the CG's minimum zoom, 1.0 stored as its bits
    ('  (&DAT_00de8f70)[param_1] = 0x3f800000;', '  (&DAT_00de8f70)[param_1] = 1.0f;'),
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
    # 0x454f80: one 0x130 byte text buffer that Ghidra split where the code patches single characters
    ('  signed char local_134 [4];\n  signed char local_130;\n  signed char local_12d;\n  signed char local_126;\n'
     '  signed char local_123;\n',
     '  signed char local_134 [0x130];\n  signed char &local_130 = local_134[4];\n  signed char &local_12d = local_134[7];\n'
     '  signed char &local_126 = local_134[0xe];\n  signed char &local_123 = local_134[0x11];\n'),
    # 0x453700: Ghidra took the float to int conversion (0x4af2c0, xmm0 = param_7 * 0x54a690) for a call with the
    # arguments of the draw after it: the slider knob
    ('    iVar4 = FUN_004af2c0(0x42840000,(float)uVar5 + _DAT_0054a6a4,fVar10,puVar6,param_5,1);\n'
     '    FUN_0044cba0(0x99,0x45184000,0x42f00000,\n'
     '                 (float)((double)iVar4 + (double)(&DAT_005ba790)[-(iVar4 >> 0x1f)]));\n',
     '    iVar4 = (int)(Sg0Emu::Fl(param_7) * _DAT_0054a690);\n'
     '    FUN_0044cba0(0x99,0x45184000,0x42f00000,(float)iVar4,0x42840000,(float)uVar5 + _DAT_0054a6a4,fVar10,\n'
     '                 puVar6,param_5,1);\n'),
    # 0x4533a0: Ghidra took it for __thiscall (param_1 = ECX); the alpha is the first stack argument (param_2)
    ('void FUN_004533a0(undefined4 param_1,undefined4 param_2)', 'void FUN_004533a0(undefined4 param_2,undefined4 param_1)'),
    # 0x451fe0: the backlog's scroll bar thumb is the engine backlog's (it scrolls the engine's entries)
    ('  FUN_0044cba0(0x9a,0x44f0c000,0,0x42280000,0x42d80000,0x44de0000,(float)iVar4 + DAT_005495bc,\n'
     '               0xffffff,param_1,1);\n'
     '  FUN_00446f60(0x44de0000,(float)(iVar4 + 0x42),0x42280000,0x42c00000,2,0);\n', ''),
    # 0x45ac90 (the TIPS screen's frame): three float to int conversions Ghidra merged with the draws after them
    ('  uVar1 = FUN_004af2c0();\n'
     '  uVar2 = FUN_004af2c0(1);\n'
     '  iVar3 = FUN_004af2c0(0x43f68000,0xffffff,uVar2);\n'
     '  FUN_0044cba0(7,0x44224000,0x44a22000,0x42400000,0x42400000,\n'
     '               ((float)((double)iVar3 + (&DAT_005ba790)[-(iVar3 >> 0x1f)]) + _DAT_0054a6bc) -\n'
     '               DAT_005495b0);\n',
     '  const float tf1 = std::min(DAT_005ba4d8, (float)param_1 * _DAT_0054a4b8);\n'
     '  const float tf2 = (float)iVar4 / _DAT_0054a66c;\n'
     '  uVar1 = (int)(tf2 * DAT_005495ec);\n'
     '  uVar2 = (int)(tf1 * DAT_005495ec);\n'
     '  iVar3 = (int)(tf1 * DAT_005495b0);\n'
     '  FUN_0044cba0(7,0x44224000,0x44a22000,0x42400000,0x42400000,0x43f68000,\n'
     '               ((float)iVar3 + _DAT_0054a6bc) - DAT_005495b0,0xffffff,uVar2,1);\n'),
    # 0x459eb0: dragging the TIPS list's scroll bar (a float to int conversion Ghidra lost)
    ('    FUN_004b1280();\n    DAT_016dc0ec = FUN_004af2c0();\n',
     '    DAT_016dc0ec = (int)((float)DAT_016dc108 + ((float)((&DAT_016dc0d8)[DAT_005c9734] - 0x14) / _DAT_0054a6b0) *\n'
     '                         (float)DAT_032fc808 / (float)FUN_004b1280());\n'),
    ('  iVar4 = FUN_004af2c0();\n  fVar5 = (float)((double)iVar4 + (&DAT_005ba790)[-(iVar4 >> 0x1f)]);\n',
     '  iVar4 = (int)(tf2 * DAT_00549608);\n  fVar5 = (float)iVar4;\n'),
    # 0x45dcb0: the TIPS text is a script string handle (FUN_0047f1f0) here, not its address
    ('  FUN_004673e0(param_1,0,7,0,&local_8);', '  FUN_004673e0((byte *)Sg0Emu::HandlePtr(param_1),0,7,0,&local_8);'),
    # 0x458d30: one glyph of the TIPS index letters (a script string handle here, not the address of the text)
    ('          iVar9 = FUN_004645a0(2,5);\n          iVar9 = iVar9 + uVar4 * 2;\n'
     '          local_108 = *(undefined1 *)(iVar9 + -20000);\n          local_107 = *(undefined1 *)(iVar9 + -19999);\n',
     '          const uint8_t *idx = Sg0Emu::HandlePtr(FUN_004645a0(2,5)) + uVar4 * 2;\n'
     '          local_108 = idx[-20000];\n          local_107 = idx[-19999];\n'),
    # 0x458d30: one text buffer (the tip number, an index letter) that Ghidra split into its first three bytes
    ('  undefined1 local_108;\n  undefined1 local_107;\n  undefined1 local_106;\n',
     '  undefined1 local_108_buf [0x100];\n  undefined1 &local_108 = local_108_buf[0];\n'
     '  undefined1 &local_107 = local_108_buf[1];\n  undefined1 &local_106 = local_108_buf[2];\n'),
    # 0x453700: the row number, typed as a pointer
    ('void FUN_00453700(int param_1,ushort *param_2,', 'void FUN_00453700(int param_1,intptr_t param_2,'),
    # ... and the stack slots of param_2 / param_8 reused for the hit area loop
    ('      _param_8 = 0;\n', '      int _param_8 = 0;\n      ushort *row;\n'),
    ('        param_2 = (ushort *)(&DAT_005c8e1a + iVar7);', '        row = (ushort *)(&DAT_005c8e1a + iVar7);'),
    ('FUN_00446f60((float)(*param_2 + uVar5),(float)iVar9,(float)param_2[1],',
     'FUN_00446f60((float)(*row + uVar5),(float)iVar9,(float)row[1],'),
    ('          param_2 = param_2 + 3;', '          row = row + 3;'),
]

# 0x452c00 / 0x452e10 / 0x4530b0 / 0x4533a0 (the four pages): the pulsing cursor; Ghidra lost the float to int conversion of its alpha
# (0x4af2c0 on xmm0): alpha * (pulse > 1 ? 2 - pulse : pulse)
PULSE = '(int)(DAT_016d78a8 > 1.0f ? (DAT_005ba560 - DAT_016d78a8) * (float)(int)%s : (float)(int)%s * DAT_016d78a8)'


def pulse_fixes(body):
    for addr, alpha in ((0x452c00, 'param_1'), (0x452e10, 'param_1'), (0x4530b0, 'param_1'), (0x4533a0, 'param_2')):
        m = re.search(r'(// ===== FUN_00%06x @ [0-9a-f]+\n.*?)(?=// ===== |\Z)' % addr, body, re.S)
        f = m.group(1)
        if 'uVar1 = FUN_004af2c0(1);' not in f:
            raise SystemExit('pulse fix not found in %x' % addr)
        f = f.replace('uVar1 = FUN_004af2c0(1);', 'uVar1 = ' + PULSE % (alpha, alpha) + ';')
        body = body.replace(m.group(1), f)
    return body


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
        for v in set(re.findall(r'\b([iu]Var\d+) = DAT_02ee(?:7660|7188|71a4);', f)):
            f = re.sub(r'^(\s+)(?:int|uint|undefined4) %s;' % v, r'\1intptr_t %s;' % v, f, count=1, flags=re.M)
        out.append(f)
    return ''.join(out)


def apply(body):
    body = scrwork_locals(body)
    body = blob_locals(body, 0x470620)
    body = blob_locals(body, 0x475ed0)
    if '// ===== FUN_00452c00' in body:
        body = pulse_fixes(body)
    for old, new in FIXES:
        if old not in body:
            # the fixes of functions not translated this time (the TIPS screen) do not apply; the compiler catches
            # a fix that no longer matches a translated function
            print('fix not applied: ' + old.strip().split('\n')[0][:70])
            continue
        body = body.replace(old, new)
    # pointer = &DAT_...: the emulated globals have one signedness, the pointers of the decompile another
    body = re.sub(r'\b(p[a-z]Var\d+|local_\w+) = (&_?DAT_\w+(?: [+-] [^;]+)?);', r'\1 = (decltype(\1))(\2);', body)
    # pointer = PTR_DAT_... (an address of emulated memory, Sg0Emu::EmuPtr): its explicit conversion
    body = re.sub(r'\b(p[a-z]Var\d+|local_\w+) = (\(&PTR_DAT_\w+\)\[[^;]+\]|PTR_DAT_\w+);', r'\1 = (decltype(\1))(\2);',
                  body)
    return body
