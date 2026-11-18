"""List / extract MPK v2 (MAGES package) archives; reads your own game files, contains no game data.

Usage:
  python -I mpk_tool.py ls <file.mpk> [substr]
  python -I mpk_tool.py x  <file.mpk> <name-exact> <outfile>
"""
import struct, sys, zlib


def read_toc(f):
    f.seek(0)
    hdr = f.read(0x40)
    magic = hdr[:4]
    assert magic == b"MPK\x00", magic
    minor, major, count = struct.unpack_from("<HHI", hdr, 4)
    f.seek(0x40)
    out = []
    for i in range(count):
        rec = f.read(0x100)
        comp, fid, off, csize, size = struct.unpack_from("<IIQQQ", rec, 0)
        name = rec[32:32 + 224].split(b"\0")[0].decode("utf-8", "replace")
        out.append(dict(i=i, comp=comp, id=fid, off=off, csize=csize, size=size, name=name))
    return (major, minor), out


def extract(f, e):
    f.seek(e["off"])
    data = f.read(e["csize"])
    if e["comp"]:
        data = zlib.decompress(data)
    return data


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cmd, path = sys.argv[1], sys.argv[2]
    with open(path, "rb") as f:
        ver, toc = read_toc(f)
        if cmd == "ls":
            sub = sys.argv[3] if len(sys.argv) > 3 else ""
            print("version", ver, "files", len(toc))
            for e in toc:
                if sub in e["name"]:
                    print(f'{e["id"]:6d} c={e["comp"]} {e["size"]:10d} {e["csize"]:10d} {e["name"]}')
        elif cmd == "x":
            name, outp = sys.argv[3], sys.argv[4]
            for e in toc:
                if e["name"] == name:
                    open(outp, "wb").write(extract(f, e))
                    print("wrote", outp)
                    return
            print("not found")


if __name__ == "__main__":
    main()
