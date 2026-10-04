"""Progress and evidence invariants without launching Yazi or chezmoi."""
import json
from contextlib import contextmanager
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch
from manual_backend import check, finalize, initialize, load, save, transition, view
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
        self.session.joinpath("config").mkdir()
        write(self.session / "baseline-theme.toml", "")
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

    @contextmanager
    def fresh_cases(self):
        def setup(t, git_plugin, instrument, probe):
            self.roots.append(t.root)
            for directory in ["source", "dest", "config", "state/instrument"]:
                (t.root / directory).mkdir(parents=True)
            t.source, t.dest = t.root / "source", t.root / "dest"
            t.cfg = t.root / "config/chezmoi.toml"
            if git_plugin:
                (t.root / "git-plugin").symlink_to(Path(git_plugin).resolve(strict=True))
        with patch("manual_backend.Runtime.setup", new=setup), patch("manual_backend.baseline"):
            yield

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

    def test_check_preserves_skip_but_does_not_hide_failed_diagnostics(self):
        self.request("skip", note="Font comparison deferred")
        value = self.request("check")
        self.assertEqual(value["result"]["status"], "SKIP")
        self.assertEqual(value["result"]["note"], "Font comparison deferred")
        self.snapshot["records"] = {}
        self.assertEqual(self.request("check")["result"]["status"], "FAIL")

    def test_last_step_skip_survives_details_check_and_case_change(self):
        attempt = self.state["attempts"][0]
        attempt.update(case=1, step=1, steps=[dict(status="PASS", visual="PASS"), dict(status="NOT RUN", visual="unanswered")])
        save(self.session, self.state)
        for operation in ["skip", "check"]:
            transition(self.session, operation, {"token": "0:1"})
        with self.fresh_cases():
            transition(self.session, "next", {"token": "0:1"})
        report = load(self.session)[1]
        self.assertEqual(report["results"][1], "SKIP")
        self.assertEqual(report["attempts"][report["active"]]["case"], 2)

    def test_case_change_preserves_unverified_and_error_results(self):
        for status in ["NOT RUN", "ERROR"]:
            with self.subTest(status=status):
                attempt = self.state["attempts"][0]
                attempt.update(case=1, step=1, steps=[dict(status="PASS", visual="PASS"), dict(status=status, visual="SKIP")])
                save(self.session, self.state)
                with self.fresh_cases():
                    transition(self.session, "next", {"token": "0:1"})
                self.assertEqual(load(self.session)[1]["results"][1], status)

    def test_relative_git_plugin_survives_backend_cwd_change(self):
        plugin = self.session / "git.yazi"
        plugin.mkdir()
        with self.fresh_cases(), patch("manual_backend.run", return_value="test"):
            with patch("os.getcwd", return_value=str(self.session)):
                initial = initialize(self.session, "git.yazi")
            # Later backend requests run from a different fixture directory.
            with patch("os.getcwd", return_value=str(self.fixture)):
                restarted = transition(self.session, "restart", {"token": initial["token"]})
        self.assertEqual(load(self.session)[1]["git_plugin"], str(plugin))
        self.assertEqual((Path(restarted["root"]) / "git-plugin").resolve(), plugin)
        self.assertNotEqual(initial["root"], restarted["root"])

    def test_finished_walk_reopens_on_restart_or_jump(self):
        for operation in ["restart", "jump"]:
            with self.subTest(operation=operation):
                attempt = self.state["attempts"][0]
                attempt.update(case=len(CASES) - 1, step=0, steps=[dict(status="SKIP", visual="SKIP")])
                save(self.session, self.state)
                completed = self.request("next")
                self.assertTrue(completed["finished"])
                with self.fresh_cases():
                    reopened = self.request(operation, index=0)
                self.assertFalse(reopened["finished"])
                self.assertNotEqual(reopened["root"], str(self.fixture))

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

    def test_harness_error_is_attributed_to_source_attempt_after_jump(self):
        write(self.session / "manual-error.json", json.dumps({"token": "0:1", "error": "Backend timeout"}))
        with self.fresh_cases():
            self.request("jump", index=0)
        state = load(self.session)[1]
        state["results"][0] = "PASS"
        for result in state["attempts"][-1]["steps"]:
            result.update(status="PASS", visual="PASS")
        save(self.session, state)
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            archive = finalize(self.session)
            report = json.loads((archive / "results.json").read_text())
        self.assertEqual(report["results"][2], "ERROR")
        self.assertEqual(report["results"][0], "PASS")
        self.assertEqual(report["attempts"][0]["steps"][1]["status"], "ERROR")
        self.assertEqual(report["attempts"][0]["steps"][0]["status"], "NOT RUN")
        self.assertTrue(report["attempts"][0]["failed"])

    def test_invalid_error_token_falls_back_to_current_step(self):
        for token in [None, "invalid", "-1:0", "0:-1", "99:0", "0:99", 1]:
            with self.subTest(token=token):
                write(self.session / "manual-error.json", json.dumps({"token": token, "error": "Backend timeout"}))
                with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
                    archive = finalize(self.session)
                    report = json.loads((archive / "results.json").read_text())
                self.assertEqual(report["results"][2], "ERROR")
                self.assertEqual(report["attempts"][0]["steps"][0]["status"], "ERROR")

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
