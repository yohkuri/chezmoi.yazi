"""Shared real-runtime fixture, with no third-party Python dependencies."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parent.parent
NAMES = ["clean", "local", "source", "bad", "space name", "日本語",
         'quote"name', "back\\slash", "new\nline", "carriage\rreturn", "-dash"]


def write(path, value):
    Path(path).write_bytes(value.encode() if isinstance(value, str) else value)


def read(path):
    # Do not normalize CR/LF in filenames or captured process output.
    return Path(path).read_bytes().decode()


def run(args, *, cwd=None, env=None, timeout=10):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    assert result.returncode == 0, (args, result.returncode, result.stderr.decode(errors="replace"))
    return result.stdout.decode()


def lua(value):
    """Serialize fixture values to Lua without JSON-only Unicode escapes."""
    if isinstance(value, (str, Path)):
        return '"' + ''.join(f"\\{byte:03d}" for byte in str(value).encode()) + '"'
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, dict):
        return "{" + ",".join(f"[{lua(k)}]={lua(v)}" for k, v in value.items()) + "}"
    return str(value)


def environment(root):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CHEZMOI_", "YAZI_", "PYTHON"))}
    for key, directory in {"YAZI_CONFIG_HOME": "config", "XDG_CONFIG_HOME": "config",
                           "XDG_STATE_HOME": "state", "XDG_CACHE_HOME": "cache",
                           "XDG_DATA_HOME": "data"}.items():
        env[key] = str(root / directory)
    env.update(YAZI_LOG="debug", TERM="xterm-256color", LC_ALL="C")
    return env


def chezmoi_args(root):
    return ["--config", str(root / "config/chezmoi.toml"), "--source", str(root / "source"),
            "--destination", str(root / "dest"), "--persistent-state", str(root / "chezmoi.db"),
            "--cache", str(root / "cache/chezmoi"), "--no-tty", "--no-pager",
            "--color=false", "--progress=false", "--skip-secrets=false"]


def owned(root):
    root = Path(root)
    assert stat.S_ISDIR(root.lstat().st_mode), "Fixture must be a real directory"
    root = root.resolve()
    assert re.fullmatch(r"chezmoi-yazi-test-[\w-]+", root.name), "Not a fixture directory"
    marker = root / "manual.json"
    assert stat.S_ISREG(marker.lstat().st_mode), "Missing regular fixture marker"
    assert json.loads(read(marker)) == {"version": 1, "root": str(root), "repo": str(REPO)}, "Ownership mismatch"
    return root


def stop(root):
    socket = root / "tmux.sock"
    try:
        mode = socket.lstat().st_mode
    except FileNotFoundError:
        return
    assert stat.S_ISSOCK(mode), "Unexpected socket path"
    result = subprocess.run(["tmux", "-S", str(socket), "kill-server"],
                            capture_output=True, timeout=5, env=environment(root))
    stopped = result.stderr.decode().strip() in (
        f"no server running on {socket}", f"error connecting to {socket} (Connection refused)")
    assert result.returncode == 0 or (result.returncode == 1 and stopped), result.stderr


class Runtime:
    def __init__(self, git_plugin=None, *, instrument=True, probe=True, keep=None):
        self.root = Path(tempfile.mkdtemp(prefix="chezmoi-yazi-test-")).resolve()
        self.owned_root = self.root
        self.started = False
        self.last_capture = ""
        self.last_capture_ansi = ""
        self.keep = bool(os.environ.get("KEEP_FIXTURE")) if keep is None else keep
        try:
            self.setup(git_plugin, instrument, probe)
        except BaseException:
            self.close()
            raise

    def setup(self, git_plugin, instrument, probe):
        root = self.root
        for directory in ["source", "dest", "config/plugins", "state", "cache", "data"]:
            (root / directory).mkdir(parents=True, exist_ok=True)
        self.source, self.dest = root / "source", root / "dest"
        self.cfg = root / "config/chezmoi.toml"
        write(self.cfg, "")
        self.env = environment(root)
        self.instrument = root / "state/instrument"
        self.control, self.calls = self.instrument / "control", self.instrument / "calls"
        self.barrier, self.report = self.instrument / "barrier", self.instrument / "report.json"
        self.dispatch = self.instrument / "dispatch.lua"
        self.socket = root / "tmux.sock"
        self.args = chezmoi_args(root)
        command = shutil.which("chezmoi")
        assert command, "chezmoi is required"
        if instrument:
            self.instrument.mkdir()
            wrapper = root / "chezmoi-wrapper"
            wrapped = [sys.executable, str(REPO / "test/command.py"), str(self.instrument), command]
            write(wrapper, '#!/bin/sh\nexec ' + shlex.join(wrapped) + ' "$@"\n')
            wrapper.chmod(0o700)
            command = wrapper
        (root / "config/plugins/chezmoi.yazi").symlink_to(REPO)
        opts = dict(command=command, config=self.cfg, source=self.source, destination=self.dest,
                    persistent_state=root / "chezmoi.db", cache=root / "cache/chezmoi",
                    timeout=1, cache_ttl=0.2, error_backoff=0.5)
        init = 'require("chezmoi"):setup ' + lua(opts) + '\n'
        config = '[mgr]\nshow_hidden=true\nlinemode="none"\n'
        for name in (["chezmoi", "git"] if git_plugin else ["chezmoi"]):
            for url in ["*", "*/"]:
                config += f'[[plugin.prepend_fetchers]]\nurl="{url}"\nrun="{name}"\ngroup="{name}"\n'
        if git_plugin:
            (root / "config/plugins/git.yazi").symlink_to(Path(git_plugin).resolve(strict=True))
            init += 'require("git"):setup()\n'
            write(root / "config/theme.toml", '[git]\nuntracked_sign="G "\n')
            run(["git", "-c", "init.templateDir=", "init", "--quiet", str(self.dest)], env=self.env)
        write(root / "config/init.lua", init)
        write(root / "config/yazi.toml", config)
        keys = dict(C="plugin chezmoi -- menu", R="plugin chezmoi -- refresh", Y="app:theme",
                    N="cd " + shlex.quote(str(self.dest / ".config")), B="cd " + shlex.quote(str(self.dest)),
                    G="tab_create " + shlex.quote(str(self.dest / ".config")), H="tab_switch 0")
        if probe:
            keys["T"] = "plugin probe"
        write(root / "config/keymap.toml", ''.join(
            f'[[mgr.prepend_keymap]]\non={json.dumps(k)}\nrun={json.dumps(v)}\n' for k, v in keys.items()))
        if probe:
            self.plugin("probe", dict(report=self.report, dispatch=self.dispatch))

    def plugin(self, name, values):
        text = read(REPO / f"test/{name}.lua")
        annotation = "--- @sync entry\n" if text.startswith("--- @sync entry\n") else ""
        text = text[len(annotation):]
        prefix = ''.join(f"local {key} = {lua(value)}\n" for key, value in values.items())
        directory = self.root / f"config/plugins/{name}.yazi"
        directory.mkdir(exist_ok=True)
        write(directory / "main.lua", annotation + prefix + text)

    def chezmoi(self, *args):
        return run(["chezmoi", *self.args, *map(str, args)], cwd=self.root, env=self.env)

    def tmux(self, *args):
        return run(["tmux", "-S", str(self.socket), "-f", "/dev/null", *map(str, args)],
                   cwd=self.root, env=self.env, timeout=5)

    def start(self, settle=0.7):
        assert not self.socket.exists(), "Refusing an existing socket"
        self.tmux("new-session", "-d", "-s", "test", "-x", "140", "-y", "40", "yazi", self.dest)
        self.started = True
        if settle:
            time.sleep(settle)

    def key(self, key, settle=0.1):
        self.tmux("send-keys", "-t", "test", "-l", key)
        if settle:
            time.sleep(settle)

    def capture(self, ansi=False):
        args = ["capture-pane"]
        if ansi:
            args.append("-e")
        capture = self.tmux(*args, "-p", "-t", "test")
        if ansi:
            self.last_capture_ansi = capture
        else:
            self.last_capture = capture
        return capture

    def wait_screen(self, predicate, description, timeout=10):
        deadline = time.monotonic() + timeout
        capture = ""
        while time.monotonic() < deadline:
            capture = self.capture()
            if predicate(capture):
                return capture
            time.sleep(0.05)
        raise AssertionError(f"Timed out waiting for {description}\n{capture}\n{self.logs()}")

    def alive(self):
        result = subprocess.run(
            ["tmux", "-S", str(self.socket), "-f", "/dev/null", "has-session", "-t", "test"],
            cwd=self.root, env=self.env, capture_output=True, timeout=5)
        return result.returncode == 0

    def quit(self, timeout=8):
        self.capture()
        self.capture(ansi=True)
        self.key("q", settle=0)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.alive():
                self.started = False
                return
            time.sleep(0.05)
        raise AssertionError("Yazi did not exit after q\n" + self.capture())

    def logs(self):
        return '\n'.join(read(p) for p in (self.root / "state").rglob("*.log"))

    def snapshot(self):
        self.report.unlink(missing_ok=True)
        self.key("T")
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                return json.loads(read(self.report))
            except (FileNotFoundError, json.JSONDecodeError):
                time.sleep(0.05)
        raise AssertionError("No probe response\n" + self.logs() + self.capture())

    def wait(self, predicate, timeout=8):
        deadline = time.monotonic() + timeout
        result = None
        while time.monotonic() < deadline:
            result = self.snapshot()
            if predicate(result):
                return result
            time.sleep(0.1)
        raise AssertionError(f"Runtime condition timed out: {result}\n{self.logs()}\n{self.capture()}")

    def refresh(self, predicate):
        epoch = self.snapshot()["epoch"]
        self.key("R")
        return self.wait(lambda s: s["epoch"] > epoch and predicate(s))

    def process_tests(self):
        self.process_report = self.instrument / "process.json"
        self.process_pid = self.instrument / "child.pid"
        self.plugin("runner", dict(python=sys.executable, script=REPO / "test/child.py",
                                   pid_file=self.process_pid, report=self.process_report))

    def check_process(self, mode):
        self.process_report.unlink(missing_ok=True)
        write(self.dispatch, mode)
        self.snapshot()
        deadline = time.monotonic() + 3
        while not self.process_report.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        result = json.loads(read(self.process_report))
        if mode == "stderr":
            assert result["output"] == "abcd\0ok\n", result
        else:
            assert result["error"] == "timeout" and result["elapsed"] < 1, result
        try:
            os.kill(int(read(self.process_pid)), 0)
        except ProcessLookupError:
            return
        raise AssertionError(f"Child survived {mode}")

    def close(self):
        assert self.root == self.owned_root and not self.root.is_symlink()
        assert re.fullmatch(r"chezmoi-yazi-test-[\w-]+", self.root.name)
        if self.started:
            stop(self.root)
        if self.keep:
            print(f"Evidence: {self.root}")
        else:
            shutil.rmtree(self.root)


@contextmanager
def fixture(git_plugin=None, **kwargs):
    instance = Runtime(git_plugin, **kwargs)
    try:
        yield instance
    finally:
        instance.close()


def baseline(t):
    """Shared initial manual/runtime state; scripts are added only after apply."""
    targets = []
    for name in NAMES:
        write(t.source / name, "original\n")
        targets.append(t.dest / name)
    write(t.root / "initial.diff", t.chezmoi("diff", *targets))
    t.chezmoi("apply", *targets)
    write(t.dest / "local", "local edit\n")
    write(t.source / "source", "source edit\n")
    write(t.dest / "unmanaged", "other\n")
    for path in [t.source / "dot_config", t.dest / ".config", t.source / "exact_dot_exact", t.dest / ".exact"]:
        path.mkdir()
    write(t.source / "dot_config/new", "new\n")
    write(t.source / "exact_dot_exact/keep", "same\n")
    write(t.dest / ".exact/keep", "same\n")
    write(t.dest / ".exact/extra", "extra\n")
    write(t.source / "symlink_link", "clean\n")
    (t.dest / "link").symlink_to("clean")
    write(t.source / "ignored", "source\n")
    write(t.source / ".chezmoiignore", "ignored\n")
    write(t.dest / "ignored", "actual\n")
    write(t.source / ".chezmoiremove", "remove-me\n")
    write(t.dest / "remove-me", "remove\n")
    write(t.source / "dot_config/run_once_pending.sh", '#!/bin/sh\ntouch ' + shlex.quote(str(t.root / "script-ran")) + '\n')
