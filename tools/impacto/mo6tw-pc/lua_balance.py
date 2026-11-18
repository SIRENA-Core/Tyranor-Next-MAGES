"""Poor man's Lua syntax sanity check (no interpreter available): bracket and block balance.

Usage: python lua_balance.py <file.lua>...
"""
import re, sys

def strip(t):
    out = []; i = 0; n = len(t)
    while i < n:
        c = t[i]
        if t.startswith('--', i):
            if t.startswith('--[[', i):
                j = t.find(']]', i); i = n if j < 0 else j + 2
            else:
                j = t.find('\n', i); i = n if j < 0 else j
        elif c in '"\'':
            j = i + 1
            while j < n and t[j] != c:
                if t[j] == chr(92): j += 1
                if t[j] == '\n': raise ValueError("newline in string")
                j += 1
            out.append('""'); i = j + 1
        else:
            out.append(c); i += 1
    return ''.join(out)

def check(path):
    t = strip(open(path, encoding='utf8').read())
    st = []; pairs = {')': '(', ']': '[', '}': '{'}
    for ch in t:
        if ch in '([{': st.append(ch)
        elif ch in ')]}':
            if not st or st.pop() != pairs[ch]: return "bracket mismatch"
    if st: return "unclosed bracket"
    pending_do = 0; opens = 0
    for w in re.findall(r'\b(function|if|for|while|do|end)\b', t):
        if w in ('function', 'if'): opens += 1
        elif w in ('for', 'while'): opens += 1; pending_do += 1
        elif w == 'do':
            if pending_do: pending_do -= 1
            else: opens += 1
        else: opens -= 1
        if opens < 0: return "extra end"
    return "unbalanced blocks %d" % opens if opens else None

bad = 0
for p in sys.argv[1:]:
    try: r = check(p)
    except ValueError as e: r = str(e)
    if r: print("FAIL", p, r); bad += 1
print("checked", len(sys.argv) - 1, "files,", bad, "failures")
