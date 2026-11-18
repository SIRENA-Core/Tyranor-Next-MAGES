"""Find the horizontal segments and vertical bands of non-transparent pixels in a sprite sheet.

Usage: python seg.py <sheet.png>

Needs Pillow (`pip install pillow`). Used to read sprite bounds off a sheet the user extracted from their own copy of
the game when hand-placing the approximate menu coordinates. Prints `xsegs` (column ranges separated by an empty gap
of at least 40 px) and, per segment, the `(x0, y0, x1, y1)` boxes of its bands.
"""
import sys
from PIL import Image

if len(sys.argv) != 2:
    sys.exit(__doc__)
name = sys.argv[1]
im = Image.open(name).convert('RGBA'); W, H = im.size
al = im.getchannel('A'); px = al.load()
A = [[px[x, y] > 20 for x in range(W)] for y in range(H)]
cols = [any(A[y][x] for y in range(H)) for x in range(W)]
segs = []; s = None; gap = 0
for x in range(W):
    if cols[x]:
        if s is None: s = x
        gap = 0; e = x
    elif s is not None:
        gap += 1
        if gap >= 40: segs.append((s, e + 1)); s = None
if s is not None: segs.append((s, e + 1))
print(name, 'xsegs', segs)
for (x0, x1) in segs:
    ys = []; s = None
    for y in range(H + 1):
        r = y < H and any(A[y][x0:x1])
        if r and s is None: s = y
        if not r and s is not None:
            xs = [x for x in range(x0, x1) if any(A[yy][x] for yy in range(s, y))]
            ys.append((min(xs), s, max(xs) + 1, y)); s = None
    print(' band', x0, x1, ys)
