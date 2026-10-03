"""Progress and evidence invariants without launching Yazi or chezmoi."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch
from manual_backend import check, finalize, save, transition, view
from manual_cases import CASES
from support import REPO, lua, write


class ManualTests(unittest.TestCase):
    def setUp(self):
        self.roots = []
        self.session = self.root()
        self.fixture = self.root()
        self.fixture.joinpath("dest").mkdir()
        self.fixture.joinpath("source").mkdir()
        self.fixture.joinpath("state/instrument").mkdir(parents=True)
        self.session.joinpath("state").mkdir()
        self.state = dict(git_plugin=None, results=["NOT RUN"] * len(CASES), active=0, versions={}, attempts=[dict(
            case=2, step=0, root=str(self.fixture), opts={"destination": str(self.fixture / "dest")},
            call_offset=0, epoch_before=None, steps=[dict(status="NOT RUN", visual="unanswered") for _ in range(3)])])
        save(self.session, self.state)
        self.snapshot = dict(records={str(self.fixture / "dest/local"): {"xy": "MM"}})

    def root(self):
        root = Path(tempfile.mkdtemp(prefix="chezmoi-yazi-test-")).resolve()
        self.roots.append(root)
        write(root / "manual.json", json.dumps(dict(version=1, root=str(root), repo=str(REPO))))
        return root

    def tearDown(self):
        for root in self.roots:
            if root.exists():
                shutil.rmtree(root)

    def request(self, operation, **extra):
        return transition(self.session, operation, dict(token="0:0", snapshot=self.snapshot, **extra))

    def test_automatic_checks_never_supply_visual_verdict(self):
        value = self.request("check")
        self.assertEqual(value["result"]["files"], "PASS")
        self.assertEqual(value["result"]["visual"], "unanswered")
        self.assertEqual(value["result"]["status"], "NOT RUN")
        self.assertEqual(self.request("next")["step"], 1)
        self.assertEqual(self.request("pass")["result"]["status"], "PASS")

    def test_internal_state_mismatch_cannot_be_overridden_by_visual_pass(self):
        self.snapshot["records"] = {}
        value = self.request("pass")
        self.assertEqual(value["result"]["files"], "PASS")
        self.assertEqual(value["result"]["diagnostic"], "FAIL")
        self.assertEqual(value["result"]["status"], "FAIL")

    def test_failed_auto_check_still_requires_visual_verdict(self):
        self.snapshot["records"] = {}
        self.request("check")
        self.assertEqual(self.request("next")["step"], 1)

    def test_stale_request_leaves_progress_untouched(self):
        before = (self.session / "walk.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "Stale"):
            transition(self.session, "next", {"token": "previous-attempt:0"})
        self.assertEqual(before, (self.session / "walk.json").read_bytes())

    def test_declining_apply_is_verified_from_files(self):
        self.state["attempts"][0].update(case=10, step=0)
        write(self.fixture / "dest/source", "original\n")
        self.assertEqual(check(self.state, {})["files"], "PASS")
        write(self.fixture / "dest/source", "source edit\n")
        self.assertEqual(check(self.state, {})["files"], "FAIL")

    def test_skipped_step_records_reason(self):
        value = self.request("skip", note="Font comparison deferred")
        self.assertEqual(value["result"]["status"], "SKIP")
        self.assertEqual(value["result"]["note"], "Font comparison deferred")

    def test_lua_serializer_handles_nested_case_arrays(self):
        self.assertEqual(lua([{"x": [True, 2, None]}]), '{{["\\120"]={true,2,nil}}}')

    def test_failed_attempt_retained_even_after_clean_exit_choice(self):
        self.state["attempts"][0]["steps"][0]["status"] = "FAIL"
        self.state["exit"] = {"keep": False}
        save(self.session, self.state)
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            archive = finalize(self.session)
            self.assertTrue((archive / "results.json").exists())
        self.assertTrue(self.fixture.exists())
        self.assertTrue(self.session.exists())

    def test_launcher_waits_for_interrupted_child_before_archiving(self):
        from manual import open_fixture
        child = Mock()
        child.poll.return_value = None
        child.wait.side_effect = [KeyboardInterrupt, None]
        def archive(root):
            self.assertTrue(child.terminate.called)
            self.assertEqual(child.wait.call_count, 2)
            self.assertTrue(json.loads((root / "walk.json").read_text())["exit"]["keep"])
        with patch("manual.install_guide"), patch("manual.subprocess.Popen", return_value=child), patch("manual_backend.finalize", side_effect=archive):
            with self.assertRaises(KeyboardInterrupt):
                open_fixture(self.session)

    def test_harness_error_retains_fixtures_and_is_archived(self):
        self.state["exit"] = {"keep": False}
        save(self.session, self.state)
        write(self.session / "manual-error.json", json.dumps({"error": "Backend timeout"}))
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            archive = finalize(self.session)
            report = json.loads((archive / "results.json").read_text())
            self.assertEqual(report["results"][2], "ERROR")
            self.assertTrue((archive / "manual-error.json").exists())
        self.assertTrue(self.fixture.exists())

    def test_successful_cleanup_happens_after_archiving(self):
        self.state["exit"] = {"keep": False}
        save(self.session, self.state)
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            archive = finalize(self.session)
            self.assertTrue((archive / "results.json").exists())
        self.assertFalse(self.fixture.exists())
        self.assertFalse(self.session.exists())


if __name__ == "__main__":
    unittest.main()
