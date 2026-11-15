#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('check_host_manifest', Path(__file__).with_name('check-host-manifest.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

TEMPLATE = """<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application>
<activity android:name=".ImpactoLaunchActivity" android:exported="true"><intent-filter>
<action android:name="com.tyranor.next.impacto.action.RUN"/><category android:name="android.intent.category.DEFAULT"/>%s
</intent-filter></activity>
<activity android:name=".TyranorImpactoActivity" android:exported="false"/>%s
</application></manifest>"""


class ManifestTest(unittest.TestCase):
    def check(self, extra_filter='', extra_node=''):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'AndroidManifest.xml'
            path.write_text(TEMPLATE % (extra_filter, extra_node), encoding='utf-8')
            return mod.problems(path)

    def test_real_manifest_has_no_launcher_entry(self):
        self.assertEqual([], mod.problems())

    def test_clean_template_passes(self):
        self.assertEqual([], self.check())

    def test_launcher_category_is_rejected(self):
        self.assertTrue(self.check('<category android:name="android.intent.category.LAUNCHER"/>'))

    def test_main_action_is_rejected(self):
        self.assertTrue(self.check('<action android:name="android.intent.action.MAIN"/>'))

    def test_extra_exported_component_is_rejected(self):
        self.assertTrue(self.check(extra_node='<activity android:name=".Other" android:exported="true"/>'))

    def test_launcher_alias_is_rejected(self):
        alias = ('<activity-alias android:name=".Alias" android:targetActivity=".ImpactoLaunchActivity" '
                 'android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/>'
                 '<category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity-alias>')
        self.assertTrue(self.check(extra_node=alias))


if __name__ == '__main__':
    unittest.main()
