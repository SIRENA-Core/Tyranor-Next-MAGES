package com.tyranor.next.impacto;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ImpactoUserConfigTest {
    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    /** A file the engine itself wrote on a device (toml11 output): an empty [GameSettings] header, flags with '|'. */
    private static final String REAL_ENGINE_FILE = "[CommonSettings]\n"
            + "ResolutionWidth = 1280\n"
            + "ResolutionHeight = 720\n"
            + "LogFile = \"/data/data/x/files/Impacto_Log.txt\"\n"
            + "LogLvl = \"Info\"\n"
            + "LogChannels = \"All\"\n"
            + "LoggingToConsole = true\n"
            + "LoggingToFile = true\n"
            + "SwapConfirmCancelButtons = false\n"
            + "\n"
            + "[GameSettings]\n"
            + "[GameSettings.mo6tw]\n"
            + "UseVSync = true\n"
            + "PatchProfile = \"\"\n"
            + "UsePatch = false\n"
            + "Display = \"Borderless\"\n"
            + "\n"
            + "[AdvancedSettings]\n"
            + "ActiveRenderer = \"OpenGL\"\n"
            + "VideoPlayer = \"FFmpeg\"\n"
            + "ActiveAudioBackend = \"OpenAL\"\n"
            + "SubtitleAssBackend = \"LibAss\"\n"
            + "SubtitleTextBackend = \"None\"\n"
            + "SubtitleBmpBackend = \"None\"\n"
            + "\n"
            + "[EnhancementsSettings]\n"
            + "SubtitleConfig = \"Karaoke|Translation\"\n"
            + "CloseBacklogWhenReachedEnd = true\n"
            + "\n"
            + "[EnhancementsSettings.CHLCC]\n"
            + "DelusionMousePatch = true\n"
            + "\n"
            + "[EnhancementsSettings.CCLCC]\n"
            + "DelusionMousePatch = true\n";

    private static ImpactoSettings all(boolean swap, boolean vsync, boolean video, String subtitles,
                                       boolean backlog, boolean delusion, String level) {
        return new ImpactoSettings(swap, vsync, video, subtitles, backlog, delusion, level);
    }

    private static final Pattern HEADER = Pattern.compile("^\\s*\\[([^\\[\\]]+)\\]\\s*(#.*)?$");
    private static final Pattern KEY = Pattern.compile("^\\s*([A-Za-z0-9_\\-]+)\\s*=.*$");

    /** Independent check that a merge result repeats no table and no key within a table. */
    private static void assertNoDuplicates(String text) {
        Set<String> tables = new HashSet<>();
        Set<String> keys = new HashSet<>();
        String table = "";
        for (String line : text.replace("\r\n", "\n").split("\n")) {
            Matcher h = HEADER.matcher(line);
            if (h.matches()) {
                table = h.group(1).trim();
                assertTrue("duplicate table [" + table + "] in:\n" + text, tables.add(table));
                continue;
            }
            Matcher k = KEY.matcher(line);
            if (k.matches()) {
                assertTrue("duplicate key " + table + "." + k.group(1) + " in:\n" + text,
                        keys.add(table + "\0" + k.group(1)));
            }
        }
    }

    private static String merged(String existing, ImpactoSettings s, String profile) {
        String out = ImpactoUserConfig.merge(existing, s, profile);
        assertNoDuplicates(out);
        // The engine cannot read these spellings back; they must never be written.
        assertFalse(out, out.contains("SubtitleConfig = \"All\""));
        assertFalse(out, out.contains("SubtitleConfig = \"None\""));
        assertFalse(out, out.contains("SubtitleConfig = \"\""));
        return out;
    }

    private static int count(String text, String needle) {
        int n = 0;
        for (int i = text.indexOf(needle); i >= 0; i = text.indexOf(needle, i + 1)) {
            n++;
        }
        return n;
    }

    // ---- ImpactoSettings.parse: the payload is untrusted

    @Test
    public void parseAcceptsTheFullPayload() {
        ImpactoSettings s = ImpactoSettings.parse("{\"swapConfirmCancel\":true,\"vsync\":false,\"videoPlayback\":false,"
                + "\"subtitles\":\" Karaoke \",\"closeBacklogAtEnd\":false,\"delusionMouse\":false,\"logLevel\":\"Debug\"}");
        assertEquals(Boolean.TRUE, s.swapConfirmCancel);
        assertEquals(Boolean.FALSE, s.vsync);
        assertEquals(Boolean.FALSE, s.videoPlayback);
        assertEquals("karaoke", s.subtitles);
        assertEquals(Boolean.FALSE, s.closeBacklogAtEnd);
        assertEquals(Boolean.FALSE, s.delusionMouse);
        assertEquals("debug", s.logLevel);
    }

    @Test
    public void parseRejectsWrongTypesUnknownChoicesAndGarbage() {
        // strings, numbers and nulls are not coerced into booleans; unknown choices are dropped
        ImpactoSettings s = ImpactoSettings.parse("{\"swapConfirmCancel\":\"true\",\"vsync\":1,\"videoPlayback\":null,"
                + "\"subtitles\":\"none\",\"logLevel\":\"loud\",\"unknown\":true}");
        assertNull(s.swapConfirmCancel);
        assertNull(s.vsync);
        assertNull(s.videoPlayback);
        assertNull("\"none\" is not a subtitle choice: the engine cannot read an empty flag set", s.subtitles);
        assertNull(s.logLevel);
        assertNull(ImpactoSettings.parse("{\"subtitles\":true}").subtitles);
        assertNull(ImpactoSettings.parse("{\"logLevel\":5}").logLevel);
        for (String bad : new String[] {null, "", "not json", "[true]", "{\"vsync\":", "{}"}) {
            ImpactoSettings none = ImpactoSettings.parse(bad);
            assertNull(String.valueOf(bad), none.vsync);
            assertNull(String.valueOf(bad), none.logLevel);
            assertNull(String.valueOf(bad), none.subtitles);
        }
    }

    @Test
    public void parseRefusesAnOversizedPayload() {
        StringBuilder big = new StringBuilder("{\"vsync\":true,\"pad\":\"");
        for (int i = 0; i < 5000; i++) {
            big.append('x');
        }
        big.append("\"}");
        assertNull(ImpactoSettings.parse(big.toString()).vsync);
    }

    // ---- ImpactoUserConfig.merge

    @Test
    public void emptyFileGetsEveryManagedTable() {
        String out = merged("", all(true, false, false, "translation", false, false, "info"), "mo6tw");
        assertTrue(out, out.contains("[CommonSettings]"));
        assertTrue(out, out.contains("SwapConfirmCancelButtons = true"));
        assertTrue(out, out.contains("LogLvl = \"Info\""));
        assertTrue(out, out.contains("[GameSettings.mo6tw]\nUseVSync = false\n"));
        assertTrue(out, out.contains("[AdvancedSettings]\nVideoPlayer = \"None\"\n"));
        assertTrue(out, out.contains("SubtitleConfig = \"Translation\""));
        assertTrue(out, out.contains("CloseBacklogWhenReachedEnd = false"));
        // mo6tw has no delusion option, so no DelusionMousePatch table is written
        assertFalse(out, out.contains("DelusionMousePatch"));
    }

    @Test
    public void subtitleChoicesAreWrittenInTheEnginesOwnFlagFormat() {
        assertTrue(merged("", all(false, true, true, "all", true, true, "warning"), "mo6tw")
                .contains("SubtitleConfig = \"Karaoke|Translation\""));
        assertTrue(merged("", all(false, true, true, "translation", true, true, "warning"), "mo6tw")
                .contains("SubtitleConfig = \"Translation\""));
        assertTrue(merged("", all(false, true, true, "karaoke", true, true, "warning"), "mo6tw")
                .contains("SubtitleConfig = \"Karaoke\""));
        // absent: the key is left alone
        assertFalse(merged("", new ImpactoSettings(null, true, null, null, null, null, null), "mo6tw")
                .contains("SubtitleConfig"));
    }

    @Test
    public void delusionOptionOnlyForTheTwoGamesThatHaveIt() {
        ImpactoSettings off = new ImpactoSettings(null, null, null, null, null, false, null);
        String chlcc = merged("", off, "chlcc");
        assertTrue(chlcc, chlcc.contains("[EnhancementsSettings.CHLCC]\nDelusionMousePatch = false\n"));
        assertFalse(chlcc, chlcc.contains("CCLCC"));
        String cclcc = merged("", off, "cclcc");
        assertTrue(cclcc, cclcc.contains("[EnhancementsSettings.CCLCC]\nDelusionMousePatch = false\n"));
        // cclcc-switch has no such option upstream
        assertEquals("", ImpactoUserConfig.merge("", off, "cclcc-switch"));
    }

    @Test
    public void aRealEngineWrittenFileIsMergedInPlace() {
        ImpactoSettings s = all(true, false, false, "translation", false, true, "debug");
        String out = merged(REAL_ENGINE_FILE, s, "mo6tw");
        assertTrue(out, out.contains("SwapConfirmCancelButtons = true\n"));
        assertTrue(out, out.contains("LogLvl = \"Debug\"\n"));
        assertTrue(out, out.contains("UseVSync = false\n"));
        assertTrue(out, out.contains("VideoPlayer = \"None\"\n"));
        assertTrue(out, out.contains("SubtitleConfig = \"Translation\"\n"));
        assertTrue(out, out.contains("CloseBacklogWhenReachedEnd = false\n"));
        // everything the host does not manage is untouched, including the empty [GameSettings] header
        assertTrue(out, out.contains("ResolutionWidth = 1280\n"));
        assertTrue(out, out.contains("LogFile = \"/data/data/x/files/Impacto_Log.txt\"\n"));
        assertTrue(out, out.contains("[GameSettings]\n[GameSettings.mo6tw]\n"));
        assertTrue(out, out.contains("Display = \"Borderless\"\n"));
        assertTrue(out, out.contains("ActiveRenderer = \"OpenGL\"\n"));
        assertTrue(out, out.contains("[EnhancementsSettings.CCLCC]\nDelusionMousePatch = true\n"));
        // same line count: nothing was added or dropped
        assertEquals(REAL_ENGINE_FILE.split("\n").length, out.split("\n").length);
    }

    @Test
    public void mergeIsIdempotentAndPreservesCommentsAndOtherGames() {
        String existing = "# my notes\n[CommonSettings]\n# keep me\nLogLvl = \"Warning\" # inline\n\n"
                + "[GameSettings.rne]\nUseVSync = true\n";
        ImpactoSettings s = all(false, false, true, "all", true, true, "error");
        String once = merged(existing, s, "mo6tw");
        String twice = merged(once, s, "mo6tw");
        assertEquals(once, twice);
        assertTrue(once, once.startsWith("# my notes\n"));
        assertTrue(once, once.contains("# keep me\n"));
        // another game's table is left alone; this game's table is added
        assertTrue(once, once.contains("[GameSettings.rne]\nUseVSync = true\n"));
        assertTrue(once, once.contains("[GameSettings.mo6tw]\nUseVSync = false\n"));
    }

    @Test
    public void missingKeyInAnExistingTableIsInsertedInsideThatTable() {
        String existing = "[CommonSettings]\nResolutionWidth = 1280\n\n[AdvancedSettings]\nActiveRenderer = \"OpenGL\"\n";
        ImpactoSettings s = new ImpactoSettings(true, null, null, null, null, null, null);
        String out = merged(existing, s, "mo6tw");
        int common = out.indexOf("[CommonSettings]");
        int advanced = out.indexOf("[AdvancedSettings]");
        int key = out.indexOf("SwapConfirmCancelButtons = true");
        assertTrue(out, common < key && key < advanced);
    }

    @Test
    public void anInvalidSubtitleValueAlreadyInTheFileIsRepaired() {
        // an empty flag set is what the engine's own overlay can leave behind; the next write replaces it
        String existing = "[EnhancementsSettings]\nSubtitleConfig = \"\"\nCloseBacklogWhenReachedEnd = true\n";
        String out = merged(existing, new ImpactoSettings(null, null, null, "all", null, null, null), "mo6tw");
        assertTrue(out, out.contains("SubtitleConfig = \"Karaoke|Translation\"\n"));
        assertEquals(1, count(out, "SubtitleConfig"));
    }

    @Test
    public void crlfAndBomInputAreHandled() {
        ImpactoSettings s = new ImpactoSettings(null, null, null, null, null, null, "trace");
        assertEquals("[CommonSettings]\nLogLvl = \"Trace\"\n",
                merged("[CommonSettings]\r\nLogLvl = \"Warning\"\r\n", s, "mo6tw"));
        assertEquals("[CommonSettings]\nLogLvl = \"Trace\"\n",
                merged("﻿[CommonSettings]\nLogLvl = \"Warning\"\n", s, "mo6tw"));
    }

    // ---- layouts the line-based merge must not touch: never invalid TOML, never a duplicate

    private void assertReplacedCleanly(String existing, ImpactoSettings s, String profile) {
        ImpactoUserConfig.Merged m = ImpactoUserConfig.mergeDetailed(existing, s, profile);
        assertNoDuplicates(m.text);
        assertTrue("expected a clean replacement for:\n" + existing, m.replacedExisting);
        for (String managed : new String[] {"[CommonSettings]", "[AdvancedSettings]"}) {
            assertEquals(managed, 1, count(m.text, managed));
        }
    }

    @Test
    public void foreignLayoutsAreReplacedCleanlyInsteadOfCorrupted() {
        ImpactoSettings s = new ImpactoSettings(null, null, false, null, null, null, "info");
        // dotted keys / inline tables of a managed table
        assertReplacedCleanly("CommonSettings.LogLvl = \"Warning\"\nAdvancedSettings = { VideoPlayer = \"FFmpeg\" }\n", s, "mo6tw");
        // quoted header and quoted key
        assertReplacedCleanly("[\"CommonSettings\"]\nLogLvl = \"Warning\"\n", s, "mo6tw");
        assertReplacedCleanly("[CommonSettings]\n\"LogLvl\" = \"Warning\"\n[AdvancedSettings]\nVideoPlayer = \"FFmpeg\"\n", s, "mo6tw");
        // a multi-line array whose rows look like headers
        assertReplacedCleanly("[CommonSettings]\nList = [\n  [1, 2],\n  [3, 4],\n]\nLogLvl = \"Warning\"\n"
                + "[AdvancedSettings]\nVideoPlayer = \"FFmpeg\"\n", s, "mo6tw");
        // a multi-line string
        assertReplacedCleanly("[CommonSettings]\nNote = \"\"\"\n[AdvancedSettings]\n\"\"\"\nLogLvl = \"Warning\"\n", s, "mo6tw");
        // a lone carriage return line ending
        assertReplacedCleanly("[CommonSettings]\rLogLvl = \"Warning\"\r[AdvancedSettings]\rVideoPlayer = \"FFmpeg\"\r", s, "mo6tw");
        // dotted forms that would collide with the tables the host appends
        ImpactoSettings delusion = new ImpactoSettings(null, null, null, null, null, false, null);
        ImpactoUserConfig.Merged dotted = ImpactoUserConfig.mergeDetailed(
                "[EnhancementsSettings]\nCHLCC.DelusionMousePatch = true\n", delusion, "chlcc");
        assertNoDuplicates(dotted.text);
        assertTrue(dotted.replacedExisting);
        ImpactoSettings vsync = new ImpactoSettings(null, false, null, null, null, null, null);
        ImpactoUserConfig.Merged profile = ImpactoUserConfig.mergeDetailed(
                "[GameSettings]\nmo6tw.UseVSync = true\n", vsync, "mo6tw");
        assertNoDuplicates(profile.text);
        assertTrue(profile.replacedExisting);
    }

    @Test
    public void arrayOfTablesNeighboursAreLeftAlone() {
        String existing = "[[Plugin]]\nName = \"a\"\n\n[CommonSettings]\nLogLvl = \"Warning\"\n\n[[Plugin]]\nName = \"b\"\n";
        ImpactoUserConfig.Merged m = ImpactoUserConfig.mergeDetailed(existing,
                new ImpactoSettings(null, null, null, null, null, null, "error"), "mo6tw");
        assertFalse(m.replacedExisting);
        assertTrue(m.text, m.text.contains("[[Plugin]]\nName = \"a\"\n"));
        assertTrue(m.text, m.text.contains("[[Plugin]]\nName = \"b\"\n"));
        assertTrue(m.text, m.text.contains("LogLvl = \"Error\"\n"));
    }

    @Test
    public void nothingToWriteLeavesTheTextAlone() {
        String existing = "[CommonSettings]\nLogLvl = \"Warning\"\n";
        assertSame(existing, ImpactoUserConfig.merge(existing, ImpactoSettings.none(), "mo6tw"));
        assertEquals("", ImpactoUserConfig.merge(null, ImpactoSettings.none(), "mo6tw"));
    }

    // ---- ImpactoUserConfig.apply (file level)

    @Test
    public void applyCreatesTheFileAndKeepsItOnRepeat() throws Exception {
        File file = new File(new File(tmp.getRoot(), "games/abc"), ImpactoUserConfig.FILE_NAME);
        ImpactoSettings s = all(true, false, true, "all", true, true, "warning");
        ImpactoUserConfig.apply(file, s, "mo6tw");
        String first = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
        assertTrue(first, first.contains("SwapConfirmCancelButtons = true"));
        long modified = file.lastModified();
        ImpactoUserConfig.apply(file, s, "mo6tw");
        assertEquals(first, new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8));
        assertEquals(modified, file.lastModified());
        assertFalse(new File(file.getPath() + ".tmp").exists());
        assertFalse(new File(file.getPath() + ImpactoUserConfig.BACKUP_SUFFIX).exists());
    }

    @Test
    public void applyUpdatesAnExistingFileInPlaceWithoutLeavingTemporaryFiles() throws Exception {
        File file = tmp.newFile(ImpactoUserConfig.FILE_NAME);
        Files.write(file.toPath(), "[CommonSettings]\nLogLvl = \"Warning\"\nKeep = 1\n".getBytes(StandardCharsets.UTF_8));
        ImpactoUserConfig.apply(file, new ImpactoSettings(null, null, null, null, null, null, "off"), "mo6tw");
        assertEquals("[CommonSettings]\nLogLvl = \"Off\"\nKeep = 1\n",
                new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8));
        assertFalse(new File(file.getPath() + ".tmp").exists());
        assertFalse(new File(file.getPath() + ImpactoUserConfig.BACKUP_SUFFIX).exists());
    }

    @Test
    public void applyKeepsABackupWhenItHasToReplaceAForeignFile() throws Exception {
        File file = tmp.newFile(ImpactoUserConfig.FILE_NAME);
        String foreign = "CommonSettings.LogLvl = \"Warning\"\nMine = \"keep me\"\n";
        Files.write(file.toPath(), foreign.getBytes(StandardCharsets.UTF_8));
        ImpactoUserConfig.apply(file, new ImpactoSettings(null, null, null, null, null, null, "info"), "mo6tw");
        File backup = new File(file.getPath() + ImpactoUserConfig.BACKUP_SUFFIX);
        assertTrue(backup.isFile());
        assertEquals(foreign, new String(Files.readAllBytes(backup.toPath()), StandardCharsets.UTF_8));
        String now = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
        assertEquals("[CommonSettings]\nLogLvl = \"Info\"\n", now);
        assertFalse(new File(file.getPath() + ".tmp").exists());
    }

    @Test(expected = java.io.IOException.class)
    public void applyRefusesAnUnexpectedlyLargeFile() throws Exception {
        File file = tmp.newFile(ImpactoUserConfig.FILE_NAME);
        byte[] chunk = new byte[1 << 20];
        java.util.Arrays.fill(chunk, (byte) '#');
        Files.write(file.toPath(), chunk);
        Files.write(file.toPath(), new byte[] {'#', '\n'}, java.nio.file.StandardOpenOption.APPEND);
        ImpactoUserConfig.apply(file, new ImpactoSettings(null, null, null, null, null, null, "info"), "mo6tw");
    }
}
