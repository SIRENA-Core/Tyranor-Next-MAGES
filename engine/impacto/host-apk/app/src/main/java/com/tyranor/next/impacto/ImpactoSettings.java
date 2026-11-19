package com.tyranor.next.impacto;

import org.json.JSONObject;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/**
 * The user settings Tyranor Next sends with a launch request (a flat JSON object). Pure Java so it can be tested on
 * the JVM. The launcher is exported, so the payload is untrusted: only known keys of the expected type are accepted,
 * everything else is ignored, and a field that is absent or invalid stays {@code null}, which means "leave the engine's
 * own value alone".
 *
 * <p>Each field maps to one option of the engine's {@code userconfig.toml} (see {@link ImpactoUserConfig}).
 */
final class ImpactoSettings {
    static final String EXTRA_SETTINGS = "com.tyranor.next.impacto.extra.SETTINGS";
    /** Set by ImpactoLaunchActivity on the (non-exported) game activity's intent; the validated {@link #touchControls}. */
    static final String EXTRA_TOUCH_CONTROLS = "com.tyranor.next.impacto.extra.TOUCH_CONTROLS";

    /** Upstream {@code LogLevel} names, lowercase as sent by the app. */
    static final Set<String> LOG_LEVELS = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            "off", "fatal", "error", "warning", "info", "debug", "trace")));

    /**
     * Which video subtitle tracks the engine shows. Three values on purpose: the engine's {@code SubtitleConfig} is a
     * flags enum written as {@code "Karaoke|Translation"}, and "no track at all" has no spelling the engine can read
     * back, so it is not offered.
     */
    static final Set<String> SUBTITLES = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            "all", "translation", "karaoke")));

    private static final int MAX_JSON_CHARS = 2048;

    final Boolean swapConfirmCancel;
    final Boolean vsync;
    final Boolean videoPlayback;
    final String subtitles;
    final Boolean closeBacklogAtEnd;
    final Boolean delusionMouse;
    final String logLevel;
    /** Host-only (not an engine option): show the on-screen touch buttons. {@code null} means the default, on. */
    final Boolean touchControls;

    ImpactoSettings(Boolean swapConfirmCancel, Boolean vsync, Boolean videoPlayback, String subtitles,
                    Boolean closeBacklogAtEnd, Boolean delusionMouse, String logLevel) {
        this(swapConfirmCancel, vsync, videoPlayback, subtitles, closeBacklogAtEnd, delusionMouse, logLevel, null);
    }

    ImpactoSettings(Boolean swapConfirmCancel, Boolean vsync, Boolean videoPlayback, String subtitles,
                    Boolean closeBacklogAtEnd, Boolean delusionMouse, String logLevel, Boolean touchControls) {
        this.swapConfirmCancel = swapConfirmCancel;
        this.vsync = vsync;
        this.videoPlayback = videoPlayback;
        this.subtitles = subtitles;
        this.closeBacklogAtEnd = closeBacklogAtEnd;
        this.delusionMouse = delusionMouse;
        this.logLevel = logLevel;
        this.touchControls = touchControls;
    }

    static ImpactoSettings none() {
        return new ImpactoSettings(null, null, null, null, null, null, null, null);
    }

    /** @return the accepted settings; never throws, and an unusable payload yields {@link #none()}. */
    static ImpactoSettings parse(String json) {
        if (json == null || json.isEmpty() || json.length() > MAX_JSON_CHARS) {
            return none();
        }
        JSONObject root;
        try {
            root = new JSONObject(json);
        } catch (Exception e) {
            // Android's JSONException is checked, the JVM test library's is not: catch both without a multi-catch.
            return none();
        }
        return new ImpactoSettings(
                bool(root, "swapConfirmCancel"),
                bool(root, "vsync"),
                bool(root, "videoPlayback"),
                choice(root, "subtitles", SUBTITLES),
                bool(root, "closeBacklogAtEnd"),
                bool(root, "delusionMouse"),
                choice(root, "logLevel", LOG_LEVELS),
                bool(root, "touchControls"));
    }

    /** Only a real JSON boolean counts: strings, numbers and nulls are rejected rather than coerced. */
    private static Boolean bool(JSONObject root, String key) {
        Object value = root.opt(key);
        return value instanceof Boolean ? (Boolean) value : null;
    }

    /** A string that, trimmed and lowercased, is one of {@code allowed}; only the allowed spelling is returned. */
    private static String choice(JSONObject root, String key, Set<String> allowed) {
        Object value = root.opt(key);
        if (value instanceof String) {
            String normalized = ((String) value).trim().toLowerCase(Locale.ROOT);
            if (allowed.contains(normalized)) {
                return normalized;
            }
        }
        return null;
    }
}
