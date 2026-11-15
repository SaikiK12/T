"""The commit-noise summariser must count only the bot and keep the payload's order."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("cn", ROOT / "scripts/commit_noise.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def commit(author, message, date):
    return {"commit": {"author": {"name": author, "date": date}, "message": message}}


class CommitNoiseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_counts_only_the_bot(self):
        cs = [commit("github-actions[bot]", "Flow paper lanes: tick 1", "2026-11-15T00:00:00Z"),
              commit("openhands", "a real change", "2026-11-14T00:00:00Z"),
              commit("github-actions[bot]", "Carry paper lanes: tick 2", "2026-11-13T00:00:00Z")]
        s = self.m.summarise(cs)
        self.assertEqual(s["commits"], 3)
        self.assertEqual(s["bot_commits"], 2)
        self.assertAlmostEqual(s["bot_share"], 2 / 3)
        self.assertEqual(s["by_kind"], {"Flow paper lanes": 1, "Carry paper lanes": 1})

    def test_newest_and_oldest_follow_payload_order(self):
        cs = [commit("github-actions[bot]", "x: 1", "2026-11-15T00:00:00Z"),
              commit("github-actions[bot]", "x: 2", "2026-11-13T00:00:00Z")]
        s = self.m.summarise(cs)
        self.assertEqual(s["newest"], "2026-11-15T00:00:00Z")
        self.assertEqual(s["oldest"], "2026-11-13T00:00:00Z")

    def test_empty_payload_does_not_divide_by_zero(self):
        s = self.m.summarise([])
        self.assertEqual(s["bot_share"], 0.0)
        self.assertIsNone(s["newest"])

    def test_no_token_is_hardcoded(self):
        src = (ROOT / "scripts/commit_noise.py").read_text()
        self.assertIn('os.environ["GITHUB_TOKEN"]', src)
        self.assertNotIn("ghp_", src)
        self.assertNotIn("github_pat_", src)


if __name__ == "__main__":
    unittest.main()
