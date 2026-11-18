package com.tyranor.next.impacto;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Writes the settings Tyranor Next sent into the engine's {@code userconfig.toml} before the engine starts.
 *
 * <p>The engine reads that file in {@code UserConfig::Configure()}, merges it over its defaults and rewrites it, so
 * the host only has to set the managed keys; everything else in the file (the engine's own in-game choices, comments)
 * is kept. A TOML parse error in that file is fatal for the engine, so the merge must never emit invalid TOML: a file
 * in a layout it cannot edit line by line, or a result that would repeat a table or key, is replaced by a clean file
 * (the old one is kept next to it as {@code userconfig.toml.bak}). Pure Java so the text merge can be unit tested on
 * the JVM.
 *
 * <p>Managed keys (upstream {@code userconfig.cpp}):
 * <ul>
 *   <li>{@code [CommonSettings]} {@code SwapConfirmCancelButtons}, {@code LogLvl}</li>
 *   <li>{@code [GameSettings.<profile>]} {@code UseVSync}</li>
 *   <li>{@code [AdvancedSettings]} {@code VideoPlayer}</li>
 *   <li>{@code [EnhancementsSettings]} {@code SubtitleConfig}, {@code CloseBacklogWhenReachedEnd}</li>
 *   <li>{@code [EnhancementsSettings.CHLCC]} / {@code .CCLCC} {@code DelusionMousePatch} (only those two games)</li>
 * </ul>
 */
final class ImpactoUserConfig {
    static final String FILE_NAME = "userconfig.toml";
    static final String BACKUP_SUFFIX = ".bak";

    /** A plain {@code [Table]} / {@code [A.B]} header, optionally followed by a comment. */
    private static final Pattern HEADER = Pattern.compile("^\\s*\\[([^\\[\\]]+)\\]\\s*(#.*)?$");
    private static final Pattern ARRAY_TABLE = Pattern.compile("^\\s*\\[\\[.*$");
    private static final Pattern KEY_LINE = Pattern.compile("^\\s*([A-Za-z0-9_\\-]+)\\s*=.*$");
    /** The managed tables written as dotted keys or inline tables, e.g. {@code CommonSettings.LogLvl = ...}. */
    private static final Pattern MANAGED_TABLE_KEY = Pattern.compile(
            "^\\s*(CommonSettings|GameSettings|AdvancedSettings|EnhancementsSettings|CHLCC|CCLCC)\\s*[.=].*$");
    /** Any dotted key assignment ({@code a.b = 1}): the engine's own writer never emits one. */
    private static final Pattern DOTTED_KEY = Pattern.compile("^\\s*[A-Za-z0-9_\\-]+\\s*\\.\\s*[A-Za-z0-9_\\-\"']+.*=.*$");
    private static final long MAX_EXISTING_BYTES = 1L << 20;

    private ImpactoUserConfig() {
    }

    /** One {@code key = value} to set inside one table. */
    private static final class Edit {
        final String table;
        final String key;
        final String value;

        Edit(String table, String key, String value) {
            this.table = table;
            this.key = key;
            this.value = value;
        }
    }

    /** The merged text, and whether the old content had to be dropped because it could not be edited safely. */
    static final class Merged {
        final String text;
        final boolean replacedExisting;

        Merged(String text, boolean replacedExisting) {
            this.text = text;
            this.replacedExisting = replacedExisting;
        }
    }

    /**
     * Merges the managed keys into {@code existing} (may be empty).
     *
     * @return the new file text; {@code existing} unchanged when the settings carry nothing to write
     */
    static String merge(String existing, ImpactoSettings settings, String profile) {
        return mergeDetailed(existing, settings, profile).text;
    }

    static Merged mergeDetailed(String existing, ImpactoSettings settings, String profile) {
        List<Edit> edits = editsFor(settings, profile);
        if (edits.isEmpty()) {
            return new Merged(existing == null ? "" : existing, false);
        }
        String base = existing == null ? "" : existing;
        if (base.startsWith("﻿")) {
            base = base.substring(1);
        }
        boolean bareCarriageReturn = base.replace("\r\n", "\n").indexOf('\r') >= 0;
        base = base.replace("\r\n", "\n");
        boolean replaced = false;
        List<String> lines = toLines(base);
        if (bareCarriageReturn || isUnsupported(lines)) {
            // Not a layout the engine writes itself: start from a clean file rather than risk invalid TOML.
            lines = new ArrayList<>();
            replaced = !base.trim().isEmpty();
        }
        applyAll(lines, edits);
        if (hasDuplicates(lines)) {
            // Whatever made the merge repeat a table or key, a clean file is always valid.
            lines = new ArrayList<>();
            applyAll(lines, edits);
            replaced = true;
        }
        return new Merged(join(lines), replaced);
    }

    /**
     * Reads {@code file} (if any), merges the settings and replaces it atomically. When the old content cannot be
     * edited safely it is first copied to {@code <file>.bak}; if that copy fails nothing is changed.
     */
    static void apply(File file, ImpactoSettings settings, String profile) throws IOException {
        String existing = "";
        if (file.isFile()) {
            if (file.length() > MAX_EXISTING_BYTES) {
                throw new IOException("user config is unexpectedly large");
            }
            existing = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
        }
        Merged merged = mergeDetailed(existing, settings, profile);
        if (merged.text.equals(existing)) {
            return;
        }
        File parent = file.getParentFile();
        if (parent != null) {
            Files.createDirectories(parent.toPath());
        }
        if (merged.replacedExisting && file.isFile()) {
            Files.copy(file.toPath(), new File(file.getPath() + BACKUP_SUFFIX).toPath(),
                    StandardCopyOption.REPLACE_EXISTING);
        }
        File temp = new File(file.getPath() + ".tmp");
        try {
            Files.write(temp.toPath(), merged.text.getBytes(StandardCharsets.UTF_8));
            try {
                Files.move(temp.toPath(), file.toPath(), StandardCopyOption.ATOMIC_MOVE);
            } catch (AtomicMoveNotSupportedException e) {
                Files.move(temp.toPath(), file.toPath(), StandardCopyOption.REPLACE_EXISTING);
            }
        } finally {
            Files.deleteIfExists(temp.toPath());
        }
    }

    // ---- what to write

    private static List<Edit> editsFor(ImpactoSettings s, String profile) {
        List<Edit> edits = new ArrayList<>();
        if (s.swapConfirmCancel != null) {
            edits.add(new Edit("CommonSettings", "SwapConfirmCancelButtons", bool(s.swapConfirmCancel)));
        }
        if (s.logLevel != null) {
            edits.add(new Edit("CommonSettings", "LogLvl", quoted(capitalize(s.logLevel))));
        }
        if (s.vsync != null) {
            edits.add(new Edit("GameSettings." + profile, "UseVSync", bool(s.vsync)));
        }
        if (s.videoPlayback != null) {
            edits.add(new Edit("AdvancedSettings", "VideoPlayer", quoted(s.videoPlayback ? "FFmpeg" : "None")));
        }
        if (s.subtitles != null) {
            // The engine writes and reads its flags enum as names joined with '|' (a real file has
            // "Karaoke|Translation"); "All" and "None" are not names it can parse back.
            String config = "translation".equals(s.subtitles) ? "Translation"
                    : "karaoke".equals(s.subtitles) ? "Karaoke" : "Karaoke|Translation";
            edits.add(new Edit("EnhancementsSettings", "SubtitleConfig", quoted(config)));
        }
        if (s.closeBacklogAtEnd != null) {
            edits.add(new Edit("EnhancementsSettings", "CloseBacklogWhenReachedEnd", bool(s.closeBacklogAtEnd)));
        }
        if (s.delusionMouse != null) {
            // Only Chaos;Head (chlcc) and Chaos;Child (cclcc) have this option.
            if ("chlcc".equals(profile)) {
                edits.add(new Edit("EnhancementsSettings.CHLCC", "DelusionMousePatch", bool(s.delusionMouse)));
            } else if ("cclcc".equals(profile)) {
                edits.add(new Edit("EnhancementsSettings.CCLCC", "DelusionMousePatch", bool(s.delusionMouse)));
            }
        }
        return edits;
    }

    // ---- line-level merge

    private static List<String> toLines(String text) {
        List<String> lines = new ArrayList<>(Arrays.asList(text.split("\n", -1)));
        // split() leaves a trailing empty element for a file that ends with a newline; re-added on output.
        if (!lines.isEmpty() && lines.get(lines.size() - 1).isEmpty()) {
            lines.remove(lines.size() - 1);
        }
        return lines;
    }

    private static String join(List<String> lines) {
        StringBuilder out = new StringBuilder();
        for (String line : lines) {
            out.append(line).append('\n');
        }
        return out.toString();
    }

    private static void applyAll(List<String> lines, List<Edit> edits) {
        for (Map.Entry<String, List<Edit>> group : groupByTable(edits).entrySet()) {
            applyTable(lines, group.getKey(), group.getValue());
        }
    }

    private static Map<String, List<Edit>> groupByTable(List<Edit> edits) {
        Map<String, List<Edit>> groups = new LinkedHashMap<>();
        for (Edit edit : edits) {
            List<Edit> group = groups.get(edit.table);
            if (group == null) {
                group = new ArrayList<>();
                groups.put(edit.table, group);
            }
            group.add(edit);
        }
        return groups;
    }

    private static void applyTable(List<String> lines, String table, List<Edit> edits) {
        int header = findHeader(lines, table);
        if (header < 0) {
            if (!lines.isEmpty() && !lines.get(lines.size() - 1).trim().isEmpty()) {
                lines.add("");
            }
            lines.add("[" + table + "]");
            for (Edit edit : edits) {
                lines.add(edit.key + " = " + edit.value);
            }
            return;
        }
        int end = header + 1;
        while (end < lines.size() && !isHeaderLine(lines.get(end))) {
            end++;
        }
        for (Edit edit : edits) {
            Pattern keyLine = Pattern.compile("^\\s*" + Pattern.quote(edit.key) + "\\s*=.*$");
            int at = -1;
            for (int i = header + 1; i < end; i++) {
                if (keyLine.matcher(lines.get(i)).matches()) {
                    at = i;
                    break;
                }
            }
            String text = edit.key + " = " + edit.value;
            if (at >= 0) {
                lines.set(at, text);
            } else {
                lines.add(header + 1, text);
                end++;
            }
        }
    }

    private static boolean isHeaderLine(String line) {
        return HEADER.matcher(line).matches() || ARRAY_TABLE.matcher(line).matches();
    }

    private static int findHeader(List<String> lines, String table) {
        for (int i = 0; i < lines.size(); i++) {
            Matcher m = HEADER.matcher(lines.get(i));
            if (m.matches() && m.group(1).trim().equals(table)) {
                return i;
            }
        }
        return -1;
    }

    // ---- safety nets

    /**
     * True when the file has a construct the line-based merge cannot handle: quoted headers or keys, dotted keys,
     * inline tables of the managed tables, multi-line strings or arrays (their continuation lines can look like
     * headers), or a line starting with '[' that is not a plain header.
     */
    private static boolean isUnsupported(List<String> lines) {
        for (String line : lines) {
            String t = line.trim();
            if (t.isEmpty() || t.startsWith("#")) {
                continue;
            }
            if (t.contains("\"\"\"") || t.contains("'''")) {
                return true;
            }
            if (t.startsWith("[")) {
                if (ARRAY_TABLE.matcher(t).matches()) {
                    continue;
                }
                Matcher header = HEADER.matcher(t);
                if (!header.matches() || header.group(1).contains("\"") || header.group(1).contains("'")) {
                    return true;
                }
                continue;
            }
            if (t.startsWith("\"") || t.startsWith("'")) {
                return true;
            }
            if (MANAGED_TABLE_KEY.matcher(t).matches() || DOTTED_KEY.matcher(t).matches()) {
                return true;
            }
            int eq = t.indexOf('=');
            if (eq >= 0) {
                String value = t.substring(eq + 1);
                if (count(value, '[') != count(value, ']') || count(value, '{') != count(value, '}')) {
                    return true;
                }
            }
        }
        return false;
    }

    /** True when a plain table header, or a key inside one table, appears more than once. */
    private static boolean hasDuplicates(List<String> lines) {
        Set<String> tables = new HashSet<>();
        Set<String> keys = new HashSet<>();
        String current = "";
        for (String line : lines) {
            if (ARRAY_TABLE.matcher(line).matches()) {
                current = null;
                continue;
            }
            Matcher header = HEADER.matcher(line);
            if (header.matches()) {
                current = header.group(1).trim();
                if (!tables.add(current)) {
                    return true;
                }
                continue;
            }
            Matcher key = KEY_LINE.matcher(line);
            if (key.matches() && current != null && !keys.add(current + "\u0000" + key.group(1))) {
                return true;
            }
        }
        return false;
    }

    private static int count(String text, char c) {
        int n = 0;
        for (int i = 0; i < text.length(); i++) {
            if (text.charAt(i) == c) {
                n++;
            }
        }
        return n;
    }

    private static String bool(boolean value) {
        return value ? "true" : "false";
    }

    private static String quoted(String value) {
        return "\"" + value + "\"";
    }

    private static String capitalize(String value) {
        return value.substring(0, 1).toUpperCase(Locale.ROOT) + value.substring(1);
    }
}
