import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_repository import ADDON_IDS, build


class RepositoryTests(unittest.TestCase):
    def test_addon_xml_files_parse_and_target_python3(self):
        plugin = ET.parse(ROOT / "plugin.video.dinotv/addon.xml").getroot()
        repository = ET.parse(ROOT / "repository.dinotv/addon.xml").getroot()
        self.assertEqual(plugin.attrib["version"], "0.1.0")
        self.assertIsNotNone(plugin.find("./extension[@point='xbmc.python.pluginsource']"))
        self.assertIsNotNone(plugin.find("./requires/import[@addon='xbmc.python']"))
        self.assertIsNotNone(repository.find("./extension[@point='xbmc.addon.repository']/dir/info"))
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## {}".format(plugin.attrib["version"]), changelog)
        self.assertEqual(repository.attrib["version"], plugin.attrib["version"])

    def test_build_outputs_valid_repository_and_zip_hierarchy(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "addons"
            archives = build(output)
            self.assertEqual(len(archives), 2)
            ET.parse(output / "addons.xml")
            expected = hashlib.md5((output / "addons.xml").read_bytes()).hexdigest()
            self.assertEqual((output / "addons.xml.md5").read_text().strip(), expected)
            for addon_id, archive in zip(ADDON_IDS, archives):
                with zipfile.ZipFile(archive) as handle:
                    names = handle.namelist()
                    self.assertIn(addon_id + "/addon.xml", names)
                    self.assertTrue(all(name.startswith(addon_id + "/") for name in names))


if __name__ == "__main__":
    unittest.main()
