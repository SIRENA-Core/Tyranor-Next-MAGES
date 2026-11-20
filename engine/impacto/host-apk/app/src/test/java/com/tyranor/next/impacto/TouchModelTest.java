package com.tyranor.next.impacto;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.HashSet;
import java.util.Set;

/** The parts of the on-screen controls that need no Android runtime: the key catalog, value clamping, the toggle. */
public class TouchModelTest {
    @Test
    public void everyPageHasKeysWithUniqueLabels() {
        assertTrue(TouchKeys.PAGES.length >= 5);
        for (TouchKeys.Page page : TouchKeys.PAGES) {
            assertTrue(page.keys.length > 0);
            Set<String> labels = new HashSet<>();
            for (TouchKeys.Key key : page.keys) {
                assertTrue("duplicate label " + key.label, labels.add(key.label));
            }
        }
    }

    @Test
    public void keyKindsAreConsistent() {
        for (TouchKeys.Page page : TouchKeys.PAGES) {
            for (TouchKeys.Key key : page.keys) {
                if (key.kind == TouchKeys.Kind.KEY) {
                    assertTrue(key.label + " needs an Android key code", key.code > 0);
                } else {
                    assertFalse("mouse actions are never held keys", key.hold);
                    assertEquals(0, key.code);
                }
            }
        }
    }

    @Test
    public void theEngineOnlyControlsAreOnTheFirstPage() {
        // Auto, Skip, fast-forward, backlog, menu and quick save are what a touch-only player cannot otherwise reach.
        int[] needed = {
                android.view.KeyEvent.KEYCODE_FORWARD_DEL, android.view.KeyEvent.KEYCODE_E,
                android.view.KeyEvent.KEYCODE_Q, android.view.KeyEvent.KEYCODE_INSERT,
                android.view.KeyEvent.KEYCODE_1, android.view.KeyEvent.KEYCODE_F8,
        };
        Set<Integer> first = new HashSet<>();
        for (TouchKeys.Key key : TouchKeys.PAGES[0].keys) {
            first.add(key.code);
        }
        for (int code : needed) {
            assertTrue("key code " + code + " missing from the first page", first.contains(code));
        }
    }

    @Test
    public void clampPullsValuesIntoRangeAndRepairsNaN() {
        assertEquals(0.2f, TouchPrefs.clamp(-5f, 0.2f, 1f, 0.85f), 0f);
        assertEquals(1f, TouchPrefs.clamp(7f, 0.2f, 1f, 0.85f), 0f);
        assertEquals(0.5f, TouchPrefs.clamp(0.5f, 0.2f, 1f, 0.85f), 0f);
        assertEquals(0.85f, TouchPrefs.clamp(Float.NaN, 0.2f, 1f, 0.85f), 0f);
    }

    @Test
    public void touchControlsSettingAcceptsOnlyABoolean() {
        assertNull(ImpactoSettings.none().touchControls);
        assertEquals(Boolean.FALSE, ImpactoSettings.parse("{\"touchControls\":false}").touchControls);
        assertEquals(Boolean.TRUE, ImpactoSettings.parse("{\"touchControls\":true}").touchControls);
        assertNull(ImpactoSettings.parse("{\"touchControls\":\"no\"}").touchControls);
        assertNull(ImpactoSettings.parse("{\"touchControls\":0}").touchControls);
        assertNull(ImpactoSettings.parse("{}").touchControls);
    }
}
