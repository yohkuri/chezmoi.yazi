"""Progress and evidence invariants without launching Yazi or chezmoi."""
import json
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
import shutil
import tempfile
import tomllib
import unittest
from unittest.mock import Mock, patch
from manual_backend import check, details, finalize, initialize, load, main, prepare, save, start_case, transition, view
from manual_cases import CASES
from support import REPO, lua, read, write


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
        self.state = dict(version=2, case_keys=[case["key"] for case in CASES],
                          git_plugin=None, results=["NOT RUN"] * len(CASES), active=0, versions={}, attempts=[dict(
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

    def cli(self, operation, **payload):
        output = StringIO()
        with patch("sys.argv", ["manual_backend.py", str(self.session), operation, json.dumps(payload)]), patch("sys.stdout", output):
            main()
        return json.loads(output.getvalue())

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

    def test_theme_switching_preserves_readable_modes_and_git_context(self):
        from manual import configure_guide
        for git_plugin in [None, "git.yazi"]:
            with self.subTest(git_plugin=git_plugin), patch("manual_backend.initialize"):
                configure_guide(Mock(root=self.session), git_plugin)
                for theme in ["custom", "base"]:
                    prepare(None, [("theme", theme)], self.session)
                    actual = tomllib.loads(read(self.session / "config/theme.toml"))
                    for mode in ["normal", "select", "unset"]:
                        self.assertEqual(actual["mode"][mode + "_main"]["fg"], "#1e1e2e")
                        self.assertNotEqual(actual["mode"][mode + "_main"]["bg"], "#1e1e2e")
                    self.assertEqual(actual.get("git"), {"untracked_sign": "G "} if git_plugin else None)
                    self.assertEqual(actual.get("flavor"), {"dark": "manual", "light": "manual"} if theme == "custom" else None)

    def test_internal_state_mismatch_cannot_be_overridden_by_visual_pass(self):
        self.snapshot["records"] = {}
        value = self.request("pass")
        self.assertEqual(value["result"]["files"], "PASS")
        self.assertEqual(value["result"]["diagnostic"], "FAIL")
        self.assertEqual(value["result"]["status"], "FAIL")

    def test_accept_saves_pass_and_advances_without_answering_the_next_step(self):
        with patch("manual_backend.prepare_step"):
            value = self.request("accept")
        report = load(self.session)[1]
        self.assertEqual(report["attempts"][0]["steps"][0]["status"], "PASS")
        self.assertEqual(value["step"], 2)
        self.assertEqual(value["result"]["visual"], "unanswered")
        before = (self.session / "walk.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.request("accept")
        self.assertEqual(before, (self.session / "walk.json").read_bytes())

    def test_accept_stays_when_file_or_state_checks_fail(self):
        self.snapshot["records"] = {}
        value = self.request("accept")
        self.assertEqual(value["step"], 1)
        self.assertEqual(value["result"]["visual"], "PASS")
        self.assertEqual(value["result"]["status"], "FAIL")
        self.assertIn("staying", value["result"]["message"])

    def test_accept_preserves_verdict_if_preparing_next_step_fails(self):
        write(self.fixture / "attempt.json", json.dumps(dict(opts=dict(source=str(self.fixture / "source")))))
        write(self.fixture / "dest/local", "local edit\n")
        with patch("manual_backend.prepare", side_effect=RuntimeError("Preparation failed")):
            value = self.cli("accept", token="0:0", snapshot=self.snapshot)
        report = load(self.session)[1]
        saved = report["attempts"][0]
        self.assertEqual(saved["step"], 0)
        self.assertEqual(saved["steps"][0]["status"], "PASS")
        self.assertEqual(saved["steps"][1]["status"], "NOT RUN")
        self.assertNotIn("error", saved["steps"][0])
        self.assertFalse(saved.get("failed", False))
        self.assertEqual(report["preparation_errors"], [dict(operation="accept", token="0:0", case=2, step=1, error="Preparation failed")])
        self.assertIn("case 3, step 2", value["result"]["message"])
        self.assertEqual(value["result"]["status"], "PASS")
        # A retry prepares the next step without erasing the historical failure.
        self.assertEqual(self.cli("accept", token="0:0", snapshot=self.snapshot)["step"], 2)
        self.assertEqual(len(load(self.session)[1]["preparation_errors"]), 1)

    def test_case_preparation_cli_failure_preserves_existing_results(self):
        for operation, status in [("accept", "PASS"), ("skip-next", "SKIP"), ("next", "PASS"), ("jump", "PASS"),
                                  ("restart", "PASS"), ("jump", "NOT RUN"), ("restart", "NOT RUN")]:
            with self.subTest(operation=operation, status=status):
                attempt = self.state["attempts"][0]
                attempt.update(step=2, epoch_before=2)
                for result in attempt["steps"]:
                    result.update(status=status, visual=status if status in {"PASS", "SKIP"} else "unanswered")
                save(self.session, self.state)
                target = 2 if operation == "restart" else 11 if operation == "jump" else 3
                with self.fresh_cases(), patch("manual_backend.baseline", side_effect=RuntimeError("Baseline failed")):
                    value = self.cli(operation, token="0:2", index=11, snapshot=dict(self.snapshot, epoch=2, signs=dict(managed="C")))
                report = load(self.session)[1]
                self.assertEqual(len(report["attempts"]), 1)
                self.assertEqual(report["active"], 0)
                self.assertEqual(report["attempts"][0]["step"], 2)
                self.assertEqual([r["status"] for r in report["attempts"][0]["steps"]], [status] * 3)
                self.assertEqual(report["results"][2], status)
                self.assertFalse(report["attempts"][0].get("failed", False))
                self.assertEqual(report["preparation_errors"], [dict(operation=operation, token="0:2", case=target, step=0, error="Baseline failed")])
                self.assertEqual(value["result"]["status"], status)
                self.assertIn(f"case {target + 1}, step 1", value["result"]["message"])

    def test_preparation_error_history_retains_fixtures_without_changing_verdicts(self):
        write(self.fixture / "attempt.json", json.dumps(dict(opts=dict(source=str(self.fixture / "source")))))
        with patch("manual_backend.prepare", side_effect=RuntimeError("Preparation failed")):
            self.cli("accept", token="0:0", snapshot=self.snapshot)
        marker = dict(token="0:2", error="Later guide error")
        write(self.session / "manual-errors.jsonl", json.dumps(marker) + "\n")
        self.cli("baseline", token="0:0", snapshot=dict(epoch=3))
        report = load(self.session)[1]
        self.assertEqual(report["harness_errors"], [marker])
        self.assertEqual(report["attempts"][0]["steps"][2]["status"], "ERROR")
        report["attempts"][0]["opts"]["source"] = str(self.fixture / "source")
        save(self.session, report)
        output = StringIO()
        with patch("sys.stdout", output), patch("builtins.input", return_value="q"), patch("manual_backend.shutil.get_terminal_size", return_value=Mock(columns=140, lines=1000)):
            details(self.session)
        self.assertIn("PREPARATION ERRORS", output.getvalue())
        self.assertIn("case 3", output.getvalue())
        self.assertIn("step 2", output.getvalue())
        self.assertIn("Preparation failed", output.getvalue())
        # Isolate retention due to preparation history, even after a successful retry.
        report["harness_errors"] = []
        (self.session / "manual-errors.jsonl").unlink()
        for result in report["attempts"][0]["steps"]:
            result.clear()
            result.update(status="PASS", visual="PASS")
        report["attempts"][0].pop("failed", None)
        report["exit"] = dict(keep=False)
        save(self.session, report)
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            archive = finalize(self.session)
            saved = json.loads(read(archive / "results.json"))
        self.assertEqual(saved["results"][2], "PASS")
        self.assertEqual(saved["preparation_errors"], report["preparation_errors"])
        self.assertTrue(self.fixture.exists())
        self.assertTrue(self.session.exists())

    def test_case_preparation_failure_preserves_the_previous_attempt(self):
        previous = list(self.state["attempts"])
        with self.fresh_cases(), patch("manual_backend.prepare_step", side_effect=RuntimeError("Preparation failed")):
            with self.assertRaisesRegex(RuntimeError, "Preparation failed"):
                start_case(self.session, self.state, 0)
        self.assertEqual(self.state["attempts"], previous)
        self.assertEqual(self.state["active"], 0)

    def test_theme_reload_requires_the_same_acquisition_epoch(self):
        attempt = self.state["attempts"][0]
        attempt.update(step=1, epoch_before=3)
        snapshot = dict(epoch=4, signs=dict(managed="界", modified="m"))
        self.assertEqual(check(self.state, snapshot)["diagnostic"], "FAIL")
        snapshot["epoch"] = 3
        self.assertEqual(check(self.state, snapshot)["diagnostic"], "PASS")

    def test_completed_details_show_results_instead_of_old_instructions(self):
        self.state["finished"] = True
        self.state["attempts"][0]["opts"]["source"] = str(self.fixture / "source")
        save(self.session, self.state)
        output = StringIO()
        with patch("sys.stdout", output), patch("builtins.input", return_value="q"):
            details(self.session)
        self.assertIn("Walk complete", output.getvalue())
        self.assertIn("CASES", output.getvalue())
        self.assertNotIn(CASES[2]["steps"][0]["instruction"].splitlines()[0], output.getvalue())

    def test_failed_auto_check_still_requires_visual_verdict(self):
        self.snapshot["records"] = {}
        self.request("check")
        self.assertEqual(self.request("next")["step"], 1)

    def test_stale_request_leaves_progress_untouched(self):
        before = (self.session / "walk.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "Stale"):
            transition(self.session, "next", {"token": "previous-attempt:0"})
        self.assertEqual(before, (self.session / "walk.json").read_bytes())

    def test_stale_cli_request_returns_latest_view_without_changing_results(self):
        for status in ["PASS", "FAIL", "ERROR"]:
            with self.subTest(status=status):
                for result in self.state["attempts"][0]["steps"]:
                    result.update(status=status, visual="PASS")
                save(self.session, self.state)
                before = (self.session / "walk.json").read_bytes()
                output = StringIO()
                with patch("sys.argv", ["manual_backend.py", str(self.session), "check", '{"token":"older-token"}']), patch("sys.stdout", output):
                    main()
                value = json.loads(output.getvalue())
                self.assertEqual(value["token"], "0:0")
                self.assertEqual(value["result"]["status"], status)
                self.assertIn("Stale", value["result"]["message"])
                self.assertEqual(value["cases"][2]["result"], status)
                self.assertEqual(before, (self.session / "walk.json").read_bytes())

    def test_declining_apply_is_verified_from_files(self):
        self.state["attempts"][0].update(case=6, step=1)
        write(self.fixture / "dest/source", "original\n")
        self.assertEqual(check(self.state, {})["files"], "PASS")
        write(self.fixture / "dest/source", "source edit\n")
        self.assertEqual(check(self.state, {})["files"], "FAIL")

    def test_skipped_step_records_reason(self):
        value = self.request("skip", note="Font comparison deferred")
        self.assertEqual(value["step"], 1)
        self.assertEqual(value["result"]["status"], "SKIP")
        self.assertEqual(value["result"]["note"], "Font comparison deferred")

    def test_skip_next_does_not_check_or_answer_the_following_step(self):
        with patch("manual_backend.check", side_effect=AssertionError("Skip must not check")), patch("manual_backend.prepare_step"):
            value = self.request("skip-next")
        report = load(self.session)[1]
        skipped = report["attempts"][0]["steps"][0]
        self.assertEqual(skipped["status"], "SKIP")
        self.assertEqual(skipped["visual"], "SKIP")
        self.assertEqual(skipped["note"], "Skipped by tester")
        self.assertNotIn("files", skipped)
        self.assertEqual(value["step"], 2)
        self.assertEqual(value["result"], dict(status="NOT RUN", visual="unanswered"))
        before = (self.session / "walk.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.request("skip-next")
        self.assertEqual(before, (self.session / "walk.json").read_bytes())

    def test_skip_next_preserves_skip_when_preparing_next_step_fails(self):
        write(self.fixture / "attempt.json", json.dumps(dict(opts=dict(source=str(self.fixture / "source")))))
        write(self.fixture / "dest/local", "local edit\n")
        with patch("manual_backend.prepare", side_effect=RuntimeError("Preparation failed")):
            value = self.cli("skip-next", token="0:0")
        report = load(self.session)[1]
        self.assertEqual(value["step"], 1)
        self.assertEqual(value["result"]["status"], "SKIP")
        self.assertEqual(report["attempts"][0]["steps"][1]["status"], "NOT RUN")
        self.assertEqual(report["preparation_errors"], [dict(operation="skip-next", token="0:0", case=2, step=1, error="Preparation failed")])
        self.assertEqual(self.cli("skip-next", token="0:0")["step"], 2)

    def test_skip_next_finishes_the_last_case_without_recording_pass(self):
        self.state["attempts"][0].update(case=len(CASES) - 1, steps=[dict(status="NOT RUN", visual="unanswered")])
        save(self.session, self.state)
        value = self.request("skip-next")
        report = load(self.session)[1]
        self.assertTrue(value["finished"])
        self.assertEqual(value["result"]["status"], "SKIP")
        self.assertEqual(report["results"][-1], "SKIP")

    def test_check_preserves_skip_but_does_not_hide_failed_diagnostics(self):
        self.request("skip", note="Font comparison deferred")
        value = self.request("check")
        self.assertEqual(value["result"]["status"], "SKIP")
        self.assertEqual(value["result"]["note"], "Font comparison deferred")
        self.snapshot["records"] = {}
        self.assertEqual(self.request("check")["result"]["status"], "FAIL")

    def test_last_step_skip_survives_details_check_and_case_change(self):
        attempt = self.state["attempts"][0]
        attempt.update(case=0, step=1, steps=[dict(status="PASS", visual="PASS"), dict(status="NOT RUN", visual="unanswered")])
        save(self.session, self.state)
        for operation in ["skip", "check"]:
            transition(self.session, operation, {"token": "0:1"})
        with self.fresh_cases():
            transition(self.session, "next", {"token": "0:1"})
        report = load(self.session)[1]
        self.assertEqual(report["results"][0], "SKIP")
        self.assertEqual(report["attempts"][report["active"]]["case"], 1)

    def test_case_change_preserves_unverified_and_error_results(self):
        for status in ["NOT RUN", "ERROR"]:
            with self.subTest(status=status):
                attempt = self.state["attempts"][0]
                attempt.update(case=0, step=1, steps=[dict(status="PASS", visual="PASS"), dict(status=status, visual="SKIP")])
                save(self.session, self.state)
                with self.fresh_cases():
                    transition(self.session, "next", {"token": "0:1"})
                self.assertEqual(load(self.session)[1]["results"][0], status)

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
            self.assertTrue(json.loads(read(root / "walk.json"))["exit"]["keep"])
        with patch("manual.install_guide"), patch("manual.subprocess.Popen", return_value=child), patch("manual_backend.finalize", side_effect=archive):
            with self.assertRaises(KeyboardInterrupt):
                open_fixture(self.session)

    def test_launcher_rejects_an_old_or_reordered_catalog_without_changing_saved_progress(self):
        from manual import open_fixture
        for changes in [dict(version=1, case_keys=None), dict(case_keys=list(reversed(self.state["case_keys"])) )]:
            with self.subTest(changes=changes):
                save(self.session, dict(self.state, **changes))
                before = (self.session / "walk.json").read_bytes()
                with patch("manual.subprocess.Popen") as launch, patch("manual_backend.finalize") as archive:
                    with self.assertRaisesRegex(ValueError, "older case list"):
                        open_fixture(self.session)
                launch.assert_not_called()
                archive.assert_not_called()
                self.assertEqual((self.session / "walk.json").read_bytes(), before)
                self.assertTrue(self.fixture.exists())

    def test_harness_error_retains_fixtures_and_is_archived(self):
        self.state["exit"] = {"keep": False}
        save(self.session, self.state)
        write(self.session / "manual-error.json", json.dumps({"error": "Backend timeout"}))
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            archive = finalize(self.session)
            report = json.loads(read(archive / "results.json"))
            self.assertEqual(report["results"][2], "ERROR")
            self.assertTrue((archive / "manual-error.json").exists())
        self.assertTrue(self.fixture.exists())

    def test_harness_error_is_attributed_to_source_attempt_after_jump(self):
        write(self.session / "manual-error.json", json.dumps({"token": "0:1", "error": "Backend timeout"}))
        with self.fresh_cases():
            self.request("jump", index=0)
        state = load(self.session)[1]
        for result in state["attempts"][-1]["steps"]:
            result.update(status="PASS", visual="PASS")
        save(self.session, state)
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            archive = finalize(self.session)
            report = json.loads(read(archive / "results.json"))
        self.assertEqual(report["results"][2], "ERROR")
        self.assertEqual(report["results"][0], "PASS")
        self.assertEqual(report["attempts"][0]["steps"][1]["status"], "ERROR")
        self.assertEqual(report["attempts"][0]["steps"][0]["status"], "NOT RUN")
        self.assertTrue(report["attempts"][0]["failed"])

    def test_multiple_guide_errors_preserve_origin_results_and_complete_history(self):
        for result in self.state["attempts"][0]["steps"]:
            result.update(status="PASS", visual="PASS")
        save(self.session, self.state)
        first = dict(token="0:1", error="First guide error")
        second = dict(token="1:0", error="Second guide error")
        journal = self.session / "manual-errors.jsonl"
        write(journal, json.dumps(first) + "\n")
        with self.fresh_cases():
            latest = self.request("jump", index=0)
        state = load(self.session)[1]
        self.assertEqual(state["results"][2], "ERROR")
        for result in state["attempts"][-1]["steps"]:
            result.update(status="PASS", visual="PASS")
        save(self.session, state)
        with journal.open("a") as log:
            log.write(json.dumps(second) + "\n")
        transition(self.session, "baseline", dict(token=latest["token"]))
        self.assertEqual(load(self.session)[1]["results"][0], "ERROR")
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            archive = finalize(self.session)
            report = json.loads(read(archive / "results.json"))
            self.assertEqual(read(archive / "manual-errors.jsonl"), read(journal))
        self.assertEqual(report["harness_errors"], [first, second])
        self.assertEqual(report["results"][2], "ERROR")
        self.assertEqual(report["results"][0], "ERROR")
        self.assertTrue(all(attempt["failed"] for attempt in report["attempts"]))

    def test_imported_guide_error_does_not_override_successful_recheck(self):
        marker = dict(token="0:0", error="Transient guide failure")
        write(self.session / "manual-errors.jsonl", json.dumps(marker) + "\n")
        self.assertEqual(self.request("pass")["result"]["status"], "PASS")
        for result in load(self.session)[1]["attempts"][0]["steps"][1:]:
            self.assertEqual(result["status"], "NOT RUN")
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            report = json.loads(read(finalize(self.session) / "results.json"))
        self.assertEqual(report["attempts"][0]["steps"][0]["status"], "PASS")
        self.assertEqual(report["harness_errors"], [marker])
        self.assertTrue(report["attempts"][0]["failed"])
        self.assertTrue(self.fixture.exists())

    def test_backend_exception_updates_passing_case_and_saved_report(self):
        for result in self.state["attempts"][0]["steps"]:
            result.update(status="PASS", visual="PASS")
        save(self.session, self.state)
        output = StringIO()
        with patch("sys.argv", ["manual_backend.py", str(self.session), "check", '{"token":"0:0"}']), patch("sys.stdout", output), patch("manual_backend.check", side_effect=RuntimeError("Decryption failed")):
            main()
        value = json.loads(output.getvalue())
        self.assertEqual(value["result"]["status"], "ERROR")
        self.assertEqual(value["cases"][2]["result"], "ERROR")
        self.assertEqual(load(self.session)[1]["results"][2], "ERROR")
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            report = json.loads(read(finalize(self.session) / "results.json"))
        self.assertEqual(report["results"][2], "ERROR")
        self.assertTrue(report["attempts"][0]["failed"])

    def test_old_harness_error_preserves_latest_retry_result_after_case_change(self):
        for status in ["PASS", "SKIP", "NOT RUN", "FAIL", "ERROR"]:
            with self.subTest(status=status):
                save(self.session, self.state)
                write(self.session / "manual-error.json", json.dumps({"token": "0:1", "error": "Backend timeout"}))
                with self.fresh_cases():
                    retry = self.request("restart")
                    state = load(self.session)[1]
                    for result in state["attempts"][-1]["steps"]:
                        result.update(status=status, visual=status)
                    save(self.session, state)
                    transition(self.session, "jump", {"token": retry["token"], "index": 0})
                with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
                    archive = finalize(self.session)
                    report = json.loads(read(archive / "results.json"))
                    self.assertTrue((archive / "manual-error.json").exists())
                self.assertEqual(report["results"][2], status)
                self.assertEqual(report["results"][0], "NOT RUN")
                self.assertEqual(report["attempts"][0]["steps"][1]["status"], "ERROR")
                self.assertEqual(report["attempts"][0]["steps"][1]["error"], "Backend timeout")
                self.assertTrue(report["attempts"][0]["failed"])
                self.assertTrue(self.fixture.exists())

    def test_invalid_error_token_falls_back_to_current_step(self):
        for token in [None, "invalid", "-1:0", "0:-1", "99:0", "0:99", 1]:
            with self.subTest(token=token):
                write(self.session / "manual-error.json", json.dumps({"token": token, "error": "Backend timeout"}))
                with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
                    archive = finalize(self.session)
                    report = json.loads(read(archive / "results.json"))
                self.assertEqual(report["results"][2], "ERROR")
                self.assertEqual(report["attempts"][0]["steps"][0]["status"], "ERROR")

    def test_successful_cleanup_happens_after_archiving(self):
        self.state["exit"] = {"keep": False}
        save(self.session, self.state)
        action_log = "state/instrument/actions.jsonl"
        record = json.dumps(dict(argv=["chezmoi", "edit", "--", "source"], exit_code=0)) + "\n"
        write(self.fixture / action_log, record)
        with tempfile.TemporaryDirectory() as archive_repo, patch("manual_backend.REPO", Path(archive_repo)):
            archive = finalize(self.session)
            self.assertTrue((archive / "results.json").exists())
            self.assertEqual(read(archive / "attempt-1" / action_log), record)
        self.assertFalse(self.fixture.exists())
        self.assertFalse(self.session.exists())


if __name__ == "__main__":
    unittest.main()
