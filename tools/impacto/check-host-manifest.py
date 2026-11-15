#!/usr/bin/env python3
"""The host APK must have no desktop (launcher) entry and expose exactly one entry point to Tyranor Next.

Reads the source manifest as XML; the release workflow repeats the check on the built APK with aapt2.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[2] / 'engine/impacto/host-apk/app/src/main/AndroidManifest.xml'
ANDROID = '{http://schemas.android.com/apk/res/android}'
RUN_ACTION = 'com.tyranor.next.impacto.action.RUN'
LAUNCHER_CATEGORIES = (
    'android.intent.category.LAUNCHER',
    'android.intent.category.LEANBACK_LAUNCHER',
    'android.intent.category.INFO',
    'android.intent.category.HOME',
)


def problems(path=MANIFEST):
    found = []
    root = ET.parse(path).getroot()
    exported = []
    for node in root.iter():
        if node.tag in ('activity', 'activity-alias', 'service', 'receiver', 'provider'):
            if node.get(ANDROID + 'exported') == 'true':
                exported.append(node.get(ANDROID + 'name'))
        if node.tag == 'category' and node.get(ANDROID + 'name') in LAUNCHER_CATEGORIES:
            found.append('launcher-style category ' + node.get(ANDROID + 'name'))
        if node.tag == 'action' and node.get(ANDROID + 'name') == 'android.intent.action.MAIN':
            found.append('android.intent.action.MAIN is declared')
    if exported != ['.ImpactoLaunchActivity']:
        found.append('exported components must be exactly .ImpactoLaunchActivity, found %s' % exported)
    actions = [n.get(ANDROID + 'name') for n in root.iter('action')]
    if actions != [RUN_ACTION]:
        found.append('the only declared action must be %s, found %s' % (RUN_ACTION, actions))
    return found


if __name__ == '__main__':
    result = problems()
    for item in result:
        print('problem:', item)
    print('host manifest ok: no launcher entry' if not result else '%d problem(s)' % len(result))
    sys.exit(1 if result else 0)
