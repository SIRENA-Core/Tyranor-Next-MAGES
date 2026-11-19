package com.tyranor.next.impacto;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Insets;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.Looper;
import android.text.SpannableString;
import android.text.Spanned;
import android.text.style.ForegroundColorSpan;
import android.text.style.RelativeSizeSpan;
import android.text.style.StyleSpan;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.HapticFeedbackConstants;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.widget.CompoundButton;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.RelativeLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.Switch;
import android.widget.TextView;

import org.libsdl.app.SDLActivity;

import java.util.HashSet;
import java.util.Set;

/**
 * An on-screen keyboard and mouse for touch-only devices, drawn over the game by the host.
 *
 * <p>impacto reads Auto, Skip, fast-forward, quick save, the system menu and many more controls only from a
 * keyboard, pad or mouse; touch has just tap, two-finger tap, pinch and two swipes. Without this, a phone player
 * cannot reach most of them. The panel sends real keys and mouse events into SDL, so it is the same for every game
 * profile and needs no engine change: it is general, not tied to one game.
 *
 * <ul>
 *   <li>a small floating button (draggable) that opens a strip of keys, shown <b>by key name</b> with the control it
 *       has in the engine's default bindings under it; the strip expands sideways or up/down, one page at a time
 *       (common keys, navigation, F1-F12, A-Z, 0-9 with modifiers, mouse actions);</li>
 *   <li>a settings panel: opacity, size, expand direction, hints, idle fade, auto fold, virtual mouse;</li>
 *   <li>a tiny virtual mouse (an arrow you drag; tap = left click, long press = right click) for pointing at
 *       things touch cannot hover or right-click.</li>
 * </ul>
 *
 * <p>Everything is translucent and fades when idle, and only the views themselves take touches, so the game's own
 * gestures keep working everywhere else. Presses go through {@code SDLActivity.onNativeKeyDown/Up} with Android key
 * codes (see {@link TouchKeys}) and {@code SDLActivity.onNativeMouse}.
 */
final class TouchControls {
    private static final String PREFS = "tyranor_touch_controls_v2";

    /** How long a tap-type key or click stays down. The engine samples input once per frame: span a few. */
    private static final long TAP_MS = 80;
    private static final long FOLD_MS = 6000;
    private static final long FADE_MS = 2500;
    private static final long LONG_PRESS_MS = 450;

    private static final int COLLAPSED = 0;
    private static final int KEYS = 1;
    private static final int SETTINGS = 2;

    // Android MotionEvent actions/buttons as SDL's Android_OnMouse expects them.
    private static final int MOUSE_DOWN = MotionEvent.ACTION_DOWN;
    private static final int MOUSE_UP = MotionEvent.ACTION_UP;
    private static final int MOUSE_HOVER = MotionEvent.ACTION_HOVER_MOVE;
    private static final int MOUSE_SCROLL = MotionEvent.ACTION_SCROLL;
    private static final int BUTTON_PRIMARY = MotionEvent.BUTTON_PRIMARY;
    private static final int BUTTON_SECONDARY = MotionEvent.BUTTON_SECONDARY;

    private final Context context;
    private final RelativeLayout parent;
    private final TouchPrefs prefs;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final float density;
    private final int edge;
    private final Set<Integer> heldKeys = new HashSet<>();

    private final Fab fab;
    private final Pointer pointer;
    private final FrameLayout stripHost;
    private final FrameLayout settingsHost;
    private int mode = COLLAPSED;

    private final Runnable fold = new Runnable() {
        @Override
        public void run() {
            if (mode == KEYS) {
                setMode(COLLAPSED);
            }
        }
    };
    private final Runnable fadeOut = new Runnable() {
        @Override
        public void run() {
            if (mode == COLLAPSED && prefs.fade) {
                fab.animate().alpha(idleAlpha()).setDuration(400).start();
            }
        }
    };

    /** Adds the controls to {@code parent} (the SDL layout, a RelativeLayout); {@code null} if it is not one. */
    static TouchControls attach(Context context, ViewGroup parent) {
        if (!(parent instanceof RelativeLayout)) {
            return null;
        }
        return new TouchControls(context, (RelativeLayout) parent);
    }

    private TouchControls(Context context, RelativeLayout parent) {
        this.context = context;
        this.parent = parent;
        this.prefs = new TouchPrefs(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE));
        this.density = context.getResources().getDisplayMetrics().density;
        this.edge = dp(8);

        // Back to front: the mouse pointer under the panels, the floating button on top.
        pointer = new Pointer(context);
        parent.addView(pointer, new RelativeLayout.LayoutParams(dp(26), dp(26)));

        stripHost = newPopupHost();
        settingsHost = newPopupHost();
        parent.addView(stripHost, new RelativeLayout.LayoutParams(
                RelativeLayout.LayoutParams.WRAP_CONTENT, RelativeLayout.LayoutParams.WRAP_CONTENT));
        parent.addView(settingsHost, new RelativeLayout.LayoutParams(
                RelativeLayout.LayoutParams.WRAP_CONTENT, RelativeLayout.LayoutParams.WRAP_CONTENT));

        fab = new Fab(context);
        parent.addView(fab, new RelativeLayout.LayoutParams(fabSize(), fabSize()));

        buildStrip();
        buildSettings();
        applyAlpha();
        pointer.setVisibility(prefs.mouse ? View.VISIBLE : View.GONE);

        // Keep everything where the user left it when the window changes size (rotation, insets, multi-window).
        parent.addOnLayoutChangeListener(new View.OnLayoutChangeListener() {
            @Override
            public void onLayoutChange(View v, int l, int t, int r, int b, int ol, int ot, int or, int ob) {
                if (r - l != or - ol || b - t != ob - ot) {
                    place();
                }
            }
        });
        parent.post(new Runnable() {
            @Override
            public void run() {
                place();
                scheduleFade();
            }
        });
    }

    /** Re-places everything: the system bars and cutout insets change when the game goes (or leaves) immersive mode. */
    void refresh() {
        Runnable replace = new Runnable() {
            @Override
            public void run() {
                place();
            }
        };
        parent.post(replace);
        // SDL applies immersive mode a moment after the window gains focus.
        parent.postDelayed(replace, 700);
    }

    /** Releases every held key and folds the panel; call when the game loses focus or ends. */
    void release() {
        handler.removeCallbacks(fold);
        handler.removeCallbacks(fadeOut);
        for (Integer code : heldKeys) {
            keyUp(code);
        }
        heldKeys.clear();
        setMode(COLLAPSED);
    }

    // ---- sizes and alpha

    private int dp(float value) {
        return Math.round(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, value,
                context.getResources().getDisplayMetrics()));
    }

    private int fabSize() {
        return dp(44 * prefs.scale);
    }

    private float idleAlpha() {
        return prefs.fade ? Math.max(0.12f, prefs.opacity * 0.3f) : prefs.opacity;
    }

    private void applyAlpha() {
        stripHost.setAlpha(prefs.opacity);
        // The settings stay readable even at the lowest opacity: otherwise the slider could not be found again.
        settingsHost.setAlpha(Math.max(prefs.opacity, 0.75f));
        pointer.setAlpha(Math.max(prefs.opacity, 0.4f));
        fab.animate().cancel();
        fab.setAlpha(mode == COLLAPSED ? idleAlpha() : prefs.opacity);
    }

    // ---- building the panels

    private FrameLayout newPopupHost() {
        FrameLayout host = new FrameLayout(context);
        GradientDrawable background = new GradientDrawable();
        background.setColor(Color.argb(225, 16, 16, 22));
        background.setCornerRadius(dp(18));
        host.setBackground(background);
        host.setPadding(dp(4), dp(3), dp(4), dp(3));
        host.setVisibility(View.GONE);
        return host;
    }

    private void buildStrip() {
        TouchKeys.Page page = TouchKeys.PAGES[prefs.page];
        LinearLayout row = new LinearLayout(context);
        row.setOrientation(prefs.vertical ? LinearLayout.VERTICAL : LinearLayout.HORIZONTAL);

        TextView pageButton = pill(context.getString(page.title) + " ›");
        pageButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                prefs.page = (prefs.page + 1) % TouchKeys.PAGES.length;
                prefs.save();
                buildStrip();
                setMode(KEYS);
            }
        });
        row.addView(pageButton, buttonParams());
        for (TouchKeys.Key key : page.keys) {
            row.addView(newKeyButton(key), buttonParams());
        }
        TextView settingsButton = pill(context.getString(R.string.touch_settings));
        settingsButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                setMode(SETTINGS);
            }
        });
        row.addView(settingsButton, buttonParams());

        stripHost.removeAllViews();
        ViewGroup scroller = prefs.vertical ? new ScrollView(context) : new HorizontalScrollView(context);
        scroller.setOverScrollMode(View.OVER_SCROLL_NEVER);
        scroller.addView(row);
        stripHost.addView(scroller, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private LinearLayout.LayoutParams buttonParams() {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.setMargins(dp(1), dp(1), dp(1), dp(1));
        return lp;
    }

    private TextView baseButton() {
        TextView button = new TextView(context);
        button.setTextColor(Color.WHITE);
        button.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13 * prefs.scale);
        button.setGravity(Gravity.CENTER);
        button.setMinWidth(dp(40 * prefs.scale));
        button.setMinHeight(dp(38 * prefs.scale));
        button.setPadding(dp(7 * prefs.scale), 0, dp(7 * prefs.scale), 0);
        button.setSingleLine(false);
        return button;
    }

    /** A page or settings button: same size as a key but with a lighter, rounded background. */
    private TextView pill(String text) {
        TextView button = baseButton();
        button.setText(text);
        button.setTypeface(Typeface.DEFAULT_BOLD);
        GradientDrawable background = new GradientDrawable();
        background.setColor(Color.argb(70, 255, 255, 255));
        background.setCornerRadius(dp(14));
        button.setBackground(background);
        return button;
    }

    private TextView newKeyButton(final TouchKeys.Key key) {
        final TextView button = baseButton();
        SpannableString text;
        if (prefs.hints && key.hint != 0) {
            String hint = context.getString(key.hint);
            text = new SpannableString(key.label + "\n" + hint);
            int split = key.label.length();
            text.setSpan(new RelativeSizeSpan(0.68f), split + 1, text.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            text.setSpan(new ForegroundColorSpan(Color.argb(190, 255, 255, 255)), split + 1, text.length(),
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            text.setSpan(new StyleSpan(Typeface.BOLD), 0, split, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        } else {
            text = new SpannableString(key.label);
            text.setSpan(new StyleSpan(Typeface.BOLD), 0, text.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
        button.setText(text);
        button.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getActionMasked()) {
                    case MotionEvent.ACTION_DOWN:
                        v.setAlpha(0.45f);
                        v.performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY);
                        touched();
                        if (key.hold) {
                            heldKeys.add(key.code);
                            keyDown(key.code);
                        }
                        return true;
                    case MotionEvent.ACTION_UP:
                        v.setAlpha(1f);
                        if (key.hold) {
                            heldKeys.remove(key.code);
                            keyUp(key.code);
                        } else if (inside(v, event)) {
                            fire(key);
                        }
                        touched();
                        return true;
                    case MotionEvent.ACTION_CANCEL:
                        // A scroll of the strip takes the gesture over: let go of a held key.
                        v.setAlpha(1f);
                        if (key.hold && heldKeys.remove(key.code)) {
                            keyUp(key.code);
                        }
                        return true;
                    default:
                        return true;
                }
            }
        });
        return button;
    }

    private static boolean inside(View v, MotionEvent e) {
        return e.getX() >= 0 && e.getY() >= 0 && e.getX() <= v.getWidth() && e.getY() <= v.getHeight();
    }

    private void buildSettings() {
        LinearLayout column = new LinearLayout(context);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setLayoutParams(new ViewGroup.LayoutParams(dp(300), ViewGroup.LayoutParams.WRAP_CONTENT));
        column.setPadding(dp(10), dp(6), dp(10), dp(6));

        TextView title = new TextView(context);
        title.setText(R.string.touch_set_title);
        title.setTextColor(Color.WHITE);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        column.addView(title);

        column.addView(seekRow(R.string.touch_set_opacity, (int) (TouchPrefs.OPACITY_MIN * 100),
                (int) (TouchPrefs.OPACITY_MAX * 100), Math.round(prefs.opacity * 100),
                new SeekBar.OnSeekBarChangeListener() {
                    @Override
                    public void onProgressChanged(SeekBar bar, int progress, boolean fromUser) {
                        if (fromUser) {
                            prefs.opacity = TouchPrefs.clamp((progress + (int) (TouchPrefs.OPACITY_MIN * 100)) / 100f,
                                    TouchPrefs.OPACITY_MIN, TouchPrefs.OPACITY_MAX, TouchPrefs.OPACITY_DEFAULT);
                            applyAlpha();
                        }
                    }

                    @Override
                    public void onStartTrackingTouch(SeekBar bar) {
                    }

                    @Override
                    public void onStopTrackingTouch(SeekBar bar) {
                        prefs.save();
                    }
                }));
        column.addView(seekRow(R.string.touch_set_size, (int) (TouchPrefs.SCALE_MIN * 100),
                (int) (TouchPrefs.SCALE_MAX * 100), Math.round(prefs.scale * 100),
                new SeekBar.OnSeekBarChangeListener() {
                    private float pending = prefs.scale;

                    @Override
                    public void onProgressChanged(SeekBar bar, int progress, boolean fromUser) {
                        if (fromUser) {
                            pending = TouchPrefs.clamp((progress + (int) (TouchPrefs.SCALE_MIN * 100)) / 100f,
                                    TouchPrefs.SCALE_MIN, TouchPrefs.SCALE_MAX, 1f);
                        }
                    }

                    @Override
                    public void onStartTrackingTouch(SeekBar bar) {
                    }

                    @Override
                    public void onStopTrackingTouch(SeekBar bar) {
                        // Rebuilding the keys while the finger is down would make the bar jump: apply on release.
                        prefs.scale = pending;
                        prefs.save();
                        fab.setLayoutParams(new RelativeLayout.LayoutParams(fabSize(), fabSize()));
                        buildStrip();
                        place();
                    }
                }));

        LinearLayout direction = new LinearLayout(context);
        direction.setOrientation(LinearLayout.HORIZONTAL);
        direction.setGravity(Gravity.CENTER_VERTICAL);
        TextView directionLabel = label(R.string.touch_set_expand);
        direction.addView(directionLabel, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        final TextView horizontal = segment(R.string.touch_set_horizontal);
        final TextView vertical = segment(R.string.touch_set_vertical);
        View.OnClickListener choose = new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                prefs.vertical = v == vertical;
                prefs.save();
                markSegments(horizontal, vertical);
                buildStrip();
                place();
            }
        };
        horizontal.setOnClickListener(choose);
        vertical.setOnClickListener(choose);
        markSegments(horizontal, vertical);
        direction.addView(horizontal);
        direction.addView(vertical);
        column.addView(direction);

        column.addView(switchRow(R.string.touch_set_hints, prefs.hints, new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton b, boolean checked) {
                prefs.hints = checked;
                prefs.save();
                buildStrip();
            }
        }));
        column.addView(switchRow(R.string.touch_set_fade, prefs.fade, new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton b, boolean checked) {
                prefs.fade = checked;
                prefs.save();
                applyAlpha();
            }
        }));
        column.addView(switchRow(R.string.touch_set_fold, prefs.fold, new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton b, boolean checked) {
                prefs.fold = checked;
                prefs.save();
            }
        }));
        column.addView(switchRow(R.string.touch_set_mouse, prefs.mouse, new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton b, boolean checked) {
                prefs.mouse = checked;
                prefs.save();
                pointer.setVisibility(checked ? View.VISIBLE : View.GONE);
                place();
            }
        }));

        LinearLayout buttons = new LinearLayout(context);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        buttons.setGravity(Gravity.END);
        TextView reset = pill(context.getString(R.string.touch_set_reset));
        reset.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                prefs.fabX = 1f;
                prefs.fabY = 0f;
                prefs.mouseX = 0.5f;
                prefs.mouseY = 0.5f;
                prefs.save();
                place();
            }
        });
        TextView done = pill(context.getString(R.string.touch_set_done));
        done.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                setMode(KEYS);
            }
        });
        buttons.addView(reset, buttonParams());
        buttons.addView(done, buttonParams());
        column.addView(buttons);

        settingsHost.removeAllViews();
        ScrollView scroller = new ScrollView(context);
        scroller.setOverScrollMode(View.OVER_SCROLL_NEVER);
        scroller.addView(column);
        settingsHost.addView(scroller, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private TextView label(int res) {
        TextView label = new TextView(context);
        label.setText(res);
        label.setTextColor(Color.WHITE);
        label.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        return label;
    }

    private View seekRow(int labelRes, int min, int max, int value, final SeekBar.OnSeekBarChangeListener listener) {
        LinearLayout row = new LinearLayout(context);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.addView(label(labelRes), new LinearLayout.LayoutParams(dp(80), ViewGroup.LayoutParams.WRAP_CONTENT));
        SeekBar bar = new SeekBar(context);
        bar.setMax(max - min);
        bar.setProgress(value - min);
        bar.setOnSeekBarChangeListener(listener);
        row.addView(bar, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        return row;
    }

    private View switchRow(int labelRes, boolean checked, CompoundButton.OnCheckedChangeListener listener) {
        Switch toggle = new Switch(context);
        toggle.setText(labelRes);
        toggle.setTextColor(Color.WHITE);
        toggle.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        toggle.setChecked(checked);
        toggle.setOnCheckedChangeListener(listener);
        return toggle;
    }

    private TextView segment(int res) {
        TextView segment = baseButton();
        segment.setText(res);
        segment.setMinWidth(dp(56));
        return segment;
    }

    private void markSegments(TextView horizontal, TextView vertical) {
        horizontal.setBackground(segmentBackground(!prefs.vertical));
        vertical.setBackground(segmentBackground(prefs.vertical));
    }

    private GradientDrawable segmentBackground(boolean selected) {
        GradientDrawable background = new GradientDrawable();
        background.setColor(selected ? Color.argb(110, 255, 255, 255) : Color.argb(30, 255, 255, 255));
        background.setCornerRadius(dp(12));
        return background;
    }

    // ---- placement

    /** Free area for the floating button: the parent minus margins, system bars and the display cutout. */
    private int[] bounds(int size) {
        int left = edge;
        int top = edge;
        int right = parent.getWidth() - size - edge;
        int bottom = parent.getHeight() - size - edge;
        WindowInsets insets = parent.getRootWindowInsets();
        if (insets != null) {
            Insets safe = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            left += safe.left;
            top += safe.top;
            right -= safe.right;
            bottom -= safe.bottom;
        }
        return new int[] {left, top, Math.max(left, right), Math.max(top, bottom)};
    }

    private void place() {
        if (parent.getWidth() == 0 || parent.getHeight() == 0) {
            return;
        }
        int size = fabSize();
        int[] b = bounds(size);
        fab.setX(b[0] + prefs.fabX * (b[2] - b[0]));
        fab.setY(b[1] + prefs.fabY * (b[3] - b[1]));
        int ps = pointer.getLayoutParams().width;
        pointer.setX(prefs.mouseX * (parent.getWidth() - ps));
        pointer.setY(prefs.mouseY * (parent.getHeight() - ps));
        placePopup();
    }

    private void placePopup() {
        if (mode == KEYS) {
            fitAndPlace(stripHost);
        } else if (mode == SETTINGS) {
            fitAndPlace(settingsHost);
        }
    }

    /**
     * Sizes a popup to its content (capped to the room beside or above/below the floating button, the content then
     * scrolls) and puts it next to the button: sideways for a horizontal strip, above or below for a vertical one,
     * on whichever side has more room.
     */
    private void fitAndPlace(FrameLayout host) {
        int pw = parent.getWidth();
        int ph = parent.getHeight();
        if (pw == 0 || ph == 0) {
            return;
        }
        int size = fabSize();
        float gap = dp(6);
        boolean sideways = !prefs.vertical;
        boolean toLeft = fab.getX() + size / 2f > pw / 2f;
        boolean below = fab.getY() + size / 2f < ph / 2f;
        int maxW;
        int maxH;
        if (sideways) {
            maxW = (int) (toLeft ? fab.getX() - gap - edge : pw - fab.getX() - size - gap - edge);
            maxH = ph - 2 * edge;
        } else {
            maxH = (int) (below ? ph - fab.getY() - size - gap - edge : fab.getY() - gap - edge);
            maxW = pw - 2 * edge;
        }
        maxW = Math.max(maxW, dp(120));
        maxH = Math.max(maxH, dp(80));

        View content = ((ViewGroup) host.getChildAt(0)).getChildAt(0);
        // A fixed width (the settings column) must be measured at that width, as its scroller will lay it out.
        ViewGroup.LayoutParams contentParams = content.getLayoutParams();
        int widthSpec = contentParams != null && contentParams.width > 0
                ? View.MeasureSpec.makeMeasureSpec(contentParams.width, View.MeasureSpec.EXACTLY)
                : View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED);
        content.measure(widthSpec, View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED));
        int w = Math.min(content.getMeasuredWidth() + host.getPaddingLeft() + host.getPaddingRight(), maxW);
        int h = Math.min(content.getMeasuredHeight() + host.getPaddingTop() + host.getPaddingBottom(), maxH);
        host.setLayoutParams(new RelativeLayout.LayoutParams(w, h));

        float x;
        float y;
        if (sideways) {
            x = toLeft ? fab.getX() - gap - w : fab.getX() + size + gap;
            y = fab.getY() + (size - h) / 2f;
        } else {
            x = fab.getX() + (size - w) / 2f;
            y = below ? fab.getY() + size + gap : fab.getY() - gap - h;
        }
        host.setX(Math.max(edge, Math.min(x, pw - w - edge)));
        host.setY(Math.max(edge, Math.min(y, ph - h - edge)));
    }

    private void setMode(int next) {
        handler.removeCallbacks(fold);
        mode = next;
        stripHost.setVisibility(next == KEYS ? View.VISIBLE : View.GONE);
        settingsHost.setVisibility(next == SETTINGS ? View.VISIBLE : View.GONE);
        placePopup();
        if (next == KEYS && prefs.fold) {
            handler.postDelayed(fold, FOLD_MS);
        }
        touched();
    }

    /** Any interaction: show the button clearly, keep the strip open, and schedule the fade. */
    private void touched() {
        fab.animate().cancel();
        fab.setAlpha(prefs.opacity);
        if (mode == KEYS && prefs.fold) {
            handler.removeCallbacks(fold);
            handler.postDelayed(fold, FOLD_MS);
        }
        scheduleFade();
    }

    private void scheduleFade() {
        handler.removeCallbacks(fadeOut);
        handler.postDelayed(fadeOut, FADE_MS);
    }

    // ---- key and mouse injection

    private void fire(TouchKeys.Key key) {
        switch (key.kind) {
            case KEY:
                tap(key.code);
                break;
            case LEFT_CLICK:
                click(BUTTON_PRIMARY);
                break;
            case RIGHT_CLICK:
                click(BUTTON_SECONDARY);
                break;
            case WHEEL_UP:
                wheel(1f);
                break;
            case WHEEL_DOWN:
                wheel(-1f);
                break;
            default:
                break;
        }
    }

    private void tap(final int keyCode) {
        keyDown(keyCode);
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                keyUp(keyCode);
            }
        }, TAP_MS);
    }

    private static void keyDown(int keyCode) {
        if (!SDLActivity.mBrokenLibraries) {
            SDLActivity.onNativeKeyDown(keyCode);
        }
    }

    private static void keyUp(int keyCode) {
        if (!SDLActivity.mBrokenLibraries) {
            SDLActivity.onNativeKeyUp(keyCode);
        }
    }

    /** The virtual mouse's tip in the SDL surface's pixels (the surface fills the layout). */
    private float tipX() {
        return prefs.mouseX * (parent.getWidth() - pointer.getLayoutParams().width);
    }

    private float tipY() {
        return prefs.mouseY * (parent.getHeight() - pointer.getLayoutParams().width);
    }

    private void click(int button) {
        final float x = tipX();
        final float y = tipY();
        if (SDLActivity.mBrokenLibraries) {
            return;
        }
        SDLActivity.onNativeMouse(button, MOUSE_DOWN, x, y, false);
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                SDLActivity.onNativeMouse(0, MOUSE_UP, x, y, false);
            }
        }, TAP_MS);
    }

    private void wheel(float dy) {
        if (!SDLActivity.mBrokenLibraries) {
            SDLActivity.onNativeMouse(0, MOUSE_SCROLL, 0f, dy, false);
        }
    }

    private void hoverTo(float x, float y) {
        if (!SDLActivity.mBrokenLibraries) {
            SDLActivity.onNativeMouse(0, MOUSE_HOVER, x, y, false);
        }
    }

    // ---- the floating button

    /** Round translucent button with three dots; a tap folds or unfolds the panel, a drag moves it. */
    private final class Fab extends View {
        private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint ring = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint dot = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final int slop;
        private float downRawX;
        private float downRawY;
        private float startX;
        private float startY;
        private boolean dragging;

        Fab(Context context) {
            super(context);
            slop = ViewConfiguration.get(context).getScaledTouchSlop();
            fill.setColor(Color.argb(150, 12, 12, 16));
            ring.setStyle(Paint.Style.STROKE);
            ring.setStrokeWidth(density * 1.5f);
            ring.setColor(Color.argb(210, 255, 255, 255));
            dot.setColor(Color.WHITE);
        }

        @Override
        protected void onDraw(Canvas canvas) {
            float cx = getWidth() / 2f;
            float cy = getHeight() / 2f;
            float r = getWidth() * 0.34f;
            canvas.drawCircle(cx, cy, r, fill);
            canvas.drawCircle(cx, cy, r, ring);
            float d = Math.max(1.5f, r / 7f);
            canvas.drawCircle(cx - 3.2f * d, cy, d, dot);
            canvas.drawCircle(cx, cy, d, dot);
            canvas.drawCircle(cx + 3.2f * d, cy, d, dot);
        }

        @Override
        public boolean onTouchEvent(MotionEvent e) {
            switch (e.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    downRawX = e.getRawX();
                    downRawY = e.getRawY();
                    startX = getX();
                    startY = getY();
                    dragging = false;
                    touched();
                    return true;
                case MotionEvent.ACTION_MOVE: {
                    float dx = e.getRawX() - downRawX;
                    float dy = e.getRawY() - downRawY;
                    if (!dragging && Math.hypot(dx, dy) > slop) {
                        dragging = true;
                    }
                    if (dragging) {
                        int[] b = bounds(fabSize());
                        float x = Math.max(b[0], Math.min(startX + dx, b[2]));
                        float y = Math.max(b[1], Math.min(startY + dy, b[3]));
                        setX(x);
                        setY(y);
                        prefs.fabX = b[2] > b[0] ? (x - b[0]) / (b[2] - b[0]) : 1f;
                        prefs.fabY = b[3] > b[1] ? (y - b[1]) / (b[3] - b[1]) : 0f;
                        placePopup();
                        touched();
                    }
                    return true;
                }
                case MotionEvent.ACTION_UP:
                    if (dragging) {
                        prefs.save();
                    } else {
                        performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY);
                        setMode(mode == COLLAPSED ? KEYS : COLLAPSED);
                    }
                    return true;
                case MotionEvent.ACTION_CANCEL:
                    return true;
                default:
                    return super.onTouchEvent(e);
            }
        }
    }

    // ---- the virtual mouse

    /**
     * A small arrow standing for a mouse pointer: its tip (top-left corner) is the position. Drag it to move the
     * pointer, tap for a left click, hold for a right click. The engine sees an ordinary mouse.
     */
    private final class Pointer extends View {
        private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint outline = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Path arrow = new Path();
        private final int slop;
        private float downRawX;
        private float downRawY;
        private float startX;
        private float startY;
        private boolean dragging;
        private boolean longPressed;
        private final Runnable longPress = new Runnable() {
            @Override
            public void run() {
                longPressed = true;
                performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);
                click(BUTTON_SECONDARY);
            }
        };

        Pointer(Context context) {
            super(context);
            slop = ViewConfiguration.get(context).getScaledTouchSlop();
            fill.setColor(Color.WHITE);
            outline.setStyle(Paint.Style.STROKE);
            outline.setColor(Color.BLACK);
            outline.setStrokeWidth(density * 1.2f);
            outline.setStrokeJoin(Paint.Join.ROUND);
        }

        @Override
        protected void onDraw(Canvas canvas) {
            float w = getWidth();
            float h = getHeight();
            arrow.reset();
            arrow.moveTo(1f, 1f);
            arrow.lineTo(1f, h * 0.80f);
            arrow.lineTo(w * 0.22f, h * 0.62f);
            arrow.lineTo(w * 0.40f, h * 0.97f);
            arrow.lineTo(w * 0.54f, h * 0.90f);
            arrow.lineTo(w * 0.37f, h * 0.56f);
            arrow.lineTo(w * 0.66f, h * 0.56f);
            arrow.close();
            canvas.drawPath(arrow, fill);
            canvas.drawPath(arrow, outline);
        }

        @Override
        public boolean onTouchEvent(MotionEvent e) {
            switch (e.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    downRawX = e.getRawX();
                    downRawY = e.getRawY();
                    startX = getX();
                    startY = getY();
                    dragging = false;
                    longPressed = false;
                    handler.postDelayed(longPress, LONG_PRESS_MS);
                    return true;
                case MotionEvent.ACTION_MOVE: {
                    float dx = e.getRawX() - downRawX;
                    float dy = e.getRawY() - downRawY;
                    if (!dragging && !longPressed && Math.hypot(dx, dy) > slop) {
                        dragging = true;
                        handler.removeCallbacks(longPress);
                    }
                    if (dragging) {
                        int size = getWidth();
                        float x = Math.max(0, Math.min(startX + dx, parent.getWidth() - size));
                        float y = Math.max(0, Math.min(startY + dy, parent.getHeight() - size));
                        setX(x);
                        setY(y);
                        prefs.mouseX = parent.getWidth() > size ? x / (parent.getWidth() - size) : 0.5f;
                        prefs.mouseY = parent.getHeight() > size ? y / (parent.getHeight() - size) : 0.5f;
                        hoverTo(x, y);
                    }
                    return true;
                }
                case MotionEvent.ACTION_UP:
                    handler.removeCallbacks(longPress);
                    if (dragging) {
                        prefs.save();
                    } else if (!longPressed) {
                        performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY);
                        click(BUTTON_PRIMARY);
                    }
                    return true;
                case MotionEvent.ACTION_CANCEL:
                    handler.removeCallbacks(longPress);
                    return true;
                default:
                    return super.onTouchEvent(e);
            }
        }
    }
}
