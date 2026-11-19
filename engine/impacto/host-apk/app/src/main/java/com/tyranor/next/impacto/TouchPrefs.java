package com.tyranor.next.impacto;

import android.content.SharedPreferences;

/** The user's choices for the on-screen controls, kept per device (not per game: it is a property of the host). */
final class TouchPrefs {
    static final float OPACITY_MIN = 0.2f;
    static final float OPACITY_MAX = 1f;
    static final float OPACITY_DEFAULT = 0.85f;
    static final float SCALE_MIN = 0.7f;
    static final float SCALE_MAX = 1.5f;

    /** Position of the floating button as a fraction of its free area; (1, 0) is the top-right corner. */
    float fabX = 1f;
    float fabY = 0f;
    /** Position of the virtual mouse as a fraction of the screen area it can reach. */
    float mouseX = 0.5f;
    float mouseY = 0.5f;
    /** Expand the key panel downwards/upwards instead of sideways. */
    boolean vertical;
    float opacity = OPACITY_DEFAULT;
    float scale = 1f;
    boolean hints = true;
    boolean fade = true;
    boolean fold = true;
    boolean mouse;
    int page;

    private final SharedPreferences store;

    TouchPrefs(SharedPreferences store) {
        this.store = store;
        fabX = clamp(store.getFloat("fabX", fabX), 0f, 1f, 1f);
        fabY = clamp(store.getFloat("fabY", fabY), 0f, 1f, 0f);
        mouseX = clamp(store.getFloat("mouseX", mouseX), 0f, 1f, 0.5f);
        mouseY = clamp(store.getFloat("mouseY", mouseY), 0f, 1f, 0.5f);
        vertical = store.getBoolean("vertical", vertical);
        opacity = clamp(store.getFloat("opacity", opacity), OPACITY_MIN, OPACITY_MAX, OPACITY_DEFAULT);
        scale = clamp(store.getFloat("scale", scale), SCALE_MIN, SCALE_MAX, 1f);
        hints = store.getBoolean("hints", hints);
        fade = store.getBoolean("fade", fade);
        fold = store.getBoolean("fold", fold);
        mouse = store.getBoolean("mouse", mouse);
        int storedPage = store.getInt("page", 0);
        page = storedPage >= 0 && storedPage < TouchKeys.PAGES.length ? storedPage : 0;
    }

    void save() {
        store.edit()
                .putFloat("fabX", fabX).putFloat("fabY", fabY)
                .putFloat("mouseX", mouseX).putFloat("mouseY", mouseY)
                .putBoolean("vertical", vertical)
                .putFloat("opacity", opacity).putFloat("scale", scale)
                .putBoolean("hints", hints).putBoolean("fade", fade).putBoolean("fold", fold)
                .putBoolean("mouse", mouse)
                .putInt("page", page)
                .apply();
    }

    /** A value outside {@code [lo, hi]} is pulled in; NaN (a corrupt store) becomes {@code fallback}. */
    static float clamp(float value, float lo, float hi, float fallback) {
        if (Float.isNaN(value)) {
            return fallback;
        }
        return Math.max(lo, Math.min(hi, value));
    }
}
