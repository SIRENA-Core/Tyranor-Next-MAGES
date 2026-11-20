package com.tyranor.next.impacto;

import android.view.KeyEvent;

/**
 * The keys the on-screen panel can press, grouped into pages. Pure data (no views), shared by every game profile:
 * the panel sends real keyboard keys, so it works with whatever binding a profile uses, not only with one game's.
 *
 * <p>Each key is sent as an Android key code that SDL3 maps to the keyboard scancode impacto reads (SDL's
 * {@code SDL_androidkeyboard.c} table). The {@link Key#hint} is the control that key has in impacto's default
 * {@code KBcustom} table (profiles/common/scriptinput.lua), shown under the key name as a reminder; profiles that
 * ship their own table (cclcc, chlcc, mo6tw) may bind differently, which is why every key is offered and not only
 * the ones with a hint.
 */
final class TouchKeys {
    private TouchKeys() {
    }

    /** What pressing the button does. Mouse actions happen at the virtual mouse's position. */
    enum Kind {
        KEY, LEFT_CLICK, RIGHT_CLICK, WHEEL_UP, WHEEL_DOWN
    }

    static final class Key {
        final String label;
        final int code;
        final boolean hold;
        /** String resource of the control name shown under the key, or 0. */
        final int hint;
        final Kind kind;

        Key(String label, int code, boolean hold, int hint, Kind kind) {
            this.label = label;
            this.code = code;
            this.hold = hold;
            this.hint = hint;
            this.kind = kind;
        }
    }

    static final class Page {
        /** String resource of the page name. */
        final int title;
        final Key[] keys;

        Page(int title, Key... keys) {
            this.title = title;
            this.keys = keys;
        }
    }

    private static Key key(String label, int code) {
        return new Key(label, code, false, 0, Kind.KEY);
    }

    private static Key key(String label, int code, int hint) {
        return new Key(label, code, false, hint, Kind.KEY);
    }

    private static Key hold(String label, int code, int hint) {
        return new Key(label, code, true, hint, Kind.KEY);
    }

    private static Key action(String label, Kind kind) {
        return new Key(label, 0, false, 0, kind);
    }

    private static Key[] range(char first, int firstCode, int count) {
        Key[] keys = new Key[count];
        for (int i = 0; i < count; i++) {
            keys[i] = key(String.valueOf((char) (first + i)), firstCode + i);
        }
        return keys;
    }

    private static Key[] concat(Key[]... parts) {
        int n = 0;
        for (Key[] p : parts) {
            n += p.length;
        }
        Key[] all = new Key[n];
        int at = 0;
        for (Key[] p : parts) {
            System.arraycopy(p, 0, all, at, p.length);
            at += p.length;
        }
        return all;
    }

    private static Key[] functionKeys() {
        Key[] keys = new Key[12];
        for (int i = 0; i < keys.length; i++) {
            keys[i] = key("F" + (i + 1), KeyEvent.KEYCODE_F1 + i,
                    i == 7 ? R.string.touch_hint_qsave : 0);
        }
        return keys;
    }

    static final Page[] PAGES = {
            // The controls impacto only offers on a keyboard or pad; the first page is the one most players need.
            new Page(R.string.touch_page_main,
                    key("Enter", KeyEvent.KEYCODE_ENTER, R.string.touch_hint_ok),
                    key("Space", KeyEvent.KEYCODE_SPACE, R.string.touch_hint_ok),
                    key("Bksp", KeyEvent.KEYCODE_DEL, R.string.touch_hint_back),
                    key("Del", KeyEvent.KEYCODE_FORWARD_DEL, R.string.touch_hint_auto),
                    key("E", KeyEvent.KEYCODE_E, R.string.touch_hint_skip),
                    hold("Q", KeyEvent.KEYCODE_Q, R.string.touch_hint_ff),
                    key("Ins", KeyEvent.KEYCODE_INSERT, R.string.touch_hint_log),
                    key("1", KeyEvent.KEYCODE_1, R.string.touch_hint_menu),
                    key("F8", KeyEvent.KEYCODE_F8, R.string.touch_hint_qsave),
                    // Z is L2: the phone of STEINS;GATE (the scripts open it with L2 / R2), the delusions of Chaos;Child
                    key("Z", KeyEvent.KEYCODE_Z, R.string.touch_hint_phone),
                    key("Esc", KeyEvent.KEYCODE_ESCAPE),
                    hold("Ctrl", KeyEvent.KEYCODE_CTRL_LEFT, R.string.touch_hint_ff)),
            new Page(R.string.touch_page_nav,
                    key("↑", KeyEvent.KEYCODE_DPAD_UP),
                    key("↓", KeyEvent.KEYCODE_DPAD_DOWN),
                    key("←", KeyEvent.KEYCODE_DPAD_LEFT),
                    key("→", KeyEvent.KEYCODE_DPAD_RIGHT),
                    key("W", KeyEvent.KEYCODE_W),
                    key("A", KeyEvent.KEYCODE_A),
                    key("S", KeyEvent.KEYCODE_S),
                    key("D", KeyEvent.KEYCODE_D),
                    key("Home", KeyEvent.KEYCODE_MOVE_HOME),
                    key("End", KeyEvent.KEYCODE_MOVE_END),
                    key("PgUp", KeyEvent.KEYCODE_PAGE_UP),
                    key("PgDn", KeyEvent.KEYCODE_PAGE_DOWN),
                    key("Tab", KeyEvent.KEYCODE_TAB)),
            new Page(R.string.touch_page_fn, functionKeys()),
            new Page(R.string.touch_page_az, concat(
                    range('A', KeyEvent.KEYCODE_A, 26))),
            new Page(R.string.touch_page_digits, concat(
                    range('0', KeyEvent.KEYCODE_0, 10),
                    new Key[] {
                            hold("Shift", KeyEvent.KEYCODE_SHIFT_LEFT, 0),
                            hold("Ctrl", KeyEvent.KEYCODE_CTRL_LEFT, 0),
                            hold("Alt", KeyEvent.KEYCODE_ALT_LEFT, 0),
                    })),
            new Page(R.string.touch_page_mouse,
                    action("L-Click", Kind.LEFT_CLICK),
                    action("R-Click", Kind.RIGHT_CLICK),
                    action("Wheel ↑", Kind.WHEEL_UP),
                    action("Wheel ↓", Kind.WHEEL_DOWN)),
    };
}
