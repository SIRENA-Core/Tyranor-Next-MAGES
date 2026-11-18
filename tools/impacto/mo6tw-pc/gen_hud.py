"""Generate profiles/mo6tw-pc/{dialogue.lua,hud/*.lua} from profiles/mo6tw (PS3) by scaling x1.5.

Usage: python gen_hud.py <patched-impacto-checkout>

The checkout is the user's own upstream Impacto tree (pinned revision plus the patch series, or the patch branch);
files are read from and written into its profiles/ directory. No game data is read or embedded.

PC data01 (system id 4) is exactly the PS3 Data sheet x1.5, so files that only use the
Data sheet are exact. Other sheets (title, save, options, ...) were repacked on PC, so those
files are only a first approximation and carry a TODO header.
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_hud_common import scale_text

if len(sys.argv) != 2:
    sys.exit(__doc__)
root = sys.argv[1]
src = os.path.join(root, "profiles", "mo6tw")
dst = os.path.join(root, "profiles", "mo6tw-pc")

EXACT = ["hud/saveicon.lua", "hud/loadingdisplay.lua", "hud/datedisplay.lua",
         "hud/systemmenu.lua", "hud/selectiondisplay.lua", "hud/sysmesboxdisplay.lua",
         "dialogue.lua"]
APPROX = ["hud/titlemenu.lua", "hud/savemenu.lua", "hud/backlogmenu.lua",
          "hud/optionsmenu.lua", "hud/extramenus.lua"]

HDR_EXACT = ("-- Generated from profiles/mo6tw/%s by tyn gen_hud.py: coordinates x1.5\n"
             "-- (PC system.cpk data01 is the PS3 Data sheet scaled by exactly 1.5).\n")
HDR_APPROX = ("-- TODO(tyn): PC layout differs, coordinates approximate\n"
              "-- Generated from profiles/mo6tw/%s by tyn gen_hud.py: coordinates x1.5.\n"
              "-- The PC sheets for these menus were repacked, so sprite bounds are not exact.\n")

# Post-processing replacements applied after scaling: (file, old, new)
FIXUPS = {
    "dialogue.lua": [
        ("    ColorTagIsUint8 = true", "    ColorTagIsUint8 = false"),
        ("    DialogueBoxCurrentType = DialogueBoxType.MO6TW,", "    DialogueBoxCurrentType = DialogueBoxType.MO6TW,"),
    ],
}

def convert(rel, hdr):
    with open(os.path.join(src, rel), encoding="utf8", newline="") as f:
        t = f.read().replace("\r\n", "\n")
    t = scale_text(t)
    for old, new in FIXUPS.get(rel, []):
        assert old in t, (rel, old)
        t = t.replace(old, new)
    out = os.path.join(dst, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf8", newline="\n") as f:
        f.write(hdr % rel + t)
    print("wrote", out)

for r in EXACT: convert(r, HDR_EXACT)
for r in APPROX: convert(r, HDR_APPROX)
