"""Shared helpers for generating profiles/mo6tw-pc from profiles/mo6tw (x1.5 scale)."""
import re

K = 1.5

def rnd(v):
    # round half up, like an integer scale of a 1280x720 -> 1920x1080 sheet
    import math
    return math.floor(v * K + 0.5)

# Geometric keys (screen / sheet pixel units) that scale with the 1280x720 -> 1920x1080 change.
G = set("""
X Y Width Height
FirstFrameX FirstFrameY FrameWidth FrameHeight ColWidth RowHeight
firstX firstY thumbX thumbY enabledFirstX enabledFirstY disabledFirstX disabledFirstY
highlightedButtonX highlightedButtonY highlightedFirstY portraitX portraitY
weekFirstX weekFirstY weekSecondX weekSecondY weekWidth weekHeight weekFriWidth
yearNumFirstX yearNumFirstY yearNumWidth yearNum1Width yearNumHeight
numFirstX numFirstY numWidth num1Width numHeight buttonX buttonY
DateStartX MonthDayY YearWeekY
BoxX BoxY BoxMiddleBaseWidth BoxMiddleBaseX BoxMiddleRemainBase BoxMinimumWidth
BoxRightBaseX BoxRightRemainPad TextFontSize TextMiddleY TextX TextLineHeight TextMarginY
ChoicePadding ChoiceY ChoiceXBase MinMaxMesWidth AnimationSpeed
SystemMenuX SystemMenuY MenuEntriesX MenuEntriesXOffset MenuEntriesFirstY MenuEntriesYPadding
MenuEntriesTargetWidth SelectionBackgroundX SelectionYSpacing PlainSelectionYSpacing
CopyrightX CopyrightY LogoX LogoY SecondaryMenuPadding SecondaryMenuAnimUnderX
ButtonEvenX ButtonOddX CategoryEndX CategoryFontSize CheckboxFirstSectionPaddingX
CheckboxSecondSectionFirstPaddingX EntryHighlightPadding EntryStartX EntryStartY EntryXPadding
EntryYPadding FirstPageSliderMargin FontSize EndingsListTextFontSize NameFontSize NumberFontSize
NumberLabelFontSize PageSeparatorFontSize PageUpDownHeight PronunciationFontSize
SceneListFontSize SceneTitleItemsWidth ScrollAreaHeight ScrollbarStart ScrollbarThumbLength
ScrollingSpeed Spacing ThumbnailButtonTextFontSize DefaultFontSize
""".split())

ARR_KEYS = {"SelectionBackgroundY", "ThumbnailOffsets", "portraitWidths", "AutoSaveTriggerXPos"}

_stmt = re.compile(r'(?<![\w.\]])(?P<key>[A-Za-z_]\w*)(?P<eq>\s*=(?!=)\s*)(?P<rhs>[^,;{}\n]+)')
_num = re.compile(r'(?<![\w.])\d+(?:\.\d+)?(?![\w.])')
_arr = re.compile(r'(?P<head>\b(?:%s)\s*=\s*\{)(?P<body>[^}]*)(?P<tail>\})' % "|".join(ARR_KEYS))

def _scale_rhs(rhs):
    if '"' in rhs or '#' in rhs or '..' in rhs or '0x' in rhs:
        return rhs
    def f(m):
        s = m.group(0)
        v = float(s)
        if v == 0:
            return s
        return str(rnd(v))
    return _num.sub(f, rhs)

def scale_text(text):
    out = []
    for line in text.split('\n'):
        code, sep, comment = line.partition('--')
        def stmt(m):
            if m.group('key') in G:
                return m.group('key') + m.group('eq') + _scale_rhs(m.group('rhs'))
            return m.group(0)
        code = _stmt.sub(stmt, code)
        code = _arr.sub(lambda m: m.group('head') + _num.sub(lambda n: str(rnd(float(n.group(0)))), m.group('body')) + m.group('tail'), code)
        out.append(code + sep + comment)
    return '\n'.join(out)
