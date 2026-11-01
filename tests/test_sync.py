import importlib.util
import pathlib
import plistlib
import tempfile
import unittest
import zipfile

MODULE = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "sync.py"
spec = importlib.util.spec_from_file_location("ytkace_sync", MODULE)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SourceTests(unittest.TestCase):
    def test_selects_main_build_not_ios16(self):
        release = {"tag_name": "v1.1.4", "published_at": "2026-10-25T17:33:00Z", "draft": False,
                   "assets": [
                       {"name": "YTKACE_1.1.4_YouTube_iOS16_21.33.6.ipa", "browser_download_url": "https://github.com/itzzace/ytkace/releases/download/v1.1.4/a.ipa", "size": 100},
                       {"name": "YTKACE_1.1.4_YouTube_21.42.4.ipa", "browser_download_url": "https://github.com/itzzace/ytkace/releases/download/v1.1.4/b.ipa", "size": 200},
                   ]}
        chosen, asset = sync.find_latest_asset([release])
        self.assertEqual(asset["size"], 200)

    def test_feed_source_versions(self):
        release = {"tag_name": "v1.1.4", "published_at": "2026-10-25T17:33:00Z", "body": "Changes"}
        asset = {"browser_download_url": "https://github.com/itzzace/ytkace/releases/download/v1.1.4/file.ipa", "size": 121000000}
        metadata = {"CFBundleIdentifier": "com.google.ios.youtube", "CFBundleShortVersionString": "21.42.4", "CFBundleVersion": "214204", "MinimumOSVersion": "17.0"}
        source = sync.make_source({}, release, asset, metadata, "NuclearInsanity/ytkace-sidestore-source")
        self.assertEqual(source["apps"][0]["versions"][0]["version"], "21.42.4")
        self.assertEqual(source["apps"][0]["bundleIdentifier"], "com.google.ios.youtube")
        self.assertTrue(source["apps"][0]["versions"][0]["downloadURL"].startswith("https://github.com/itzzace/"))


if __name__ == "__main__":
    unittest.main()
