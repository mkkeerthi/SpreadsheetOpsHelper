from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from core import dialog
from core.adapters import BROWSE_FILETYPES
from core.dialog import DialogError, choose_file

PROJECT_ROOT = Path(dialog.__file__).resolve().parent.parent


class FakeRoot:
    def __init__(self, calls):
        self._calls = calls

    def withdraw(self):
        self._calls["withdrawn"] = True

    def attributes(self, name, value):
        self._calls.setdefault("attributes", []).append((name, value))

    def update(self):
        self._calls["updated"] = True

    def destroy(self):
        self._calls["destroyed"] = True


class MainTests(unittest.TestCase):
    """Runs the child entry point against a stub tkinter (no display needed)."""

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.folder = Path(self._temp.name)
        self.initial = str(self.folder / "book.xlsx")

    def tearDown(self):
        self._temp.cleanup()

    def _run(self, selected):
        calls = {}
        kwargs_seen = {}

        tk = types.ModuleType("tkinter")
        tk.Tk = lambda: FakeRoot(calls)
        filedialog = types.ModuleType("tkinter.filedialog")

        def askopenfilename(**kwargs):
            kwargs_seen.update(kwargs)
            return selected

        filedialog.askopenfilename = askopenfilename
        tk.filedialog = filedialog

        stdout = io.StringIO()
        with mock.patch.dict(
            sys.modules, {"tkinter": tk, "tkinter.filedialog": filedialog}
        ), mock.patch("sys.stdout", stdout):
            code = dialog.main(["core.dialog", self.initial])

        return code, stdout.getvalue(), calls, kwargs_seen

    def test_selection_is_written_to_stdout(self):
        code, stdout, calls, kwargs = self._run("/tmp/chosen.xlsx")

        self.assertEqual(code, 0)
        self.assertEqual(stdout, "/tmp/chosen.xlsx")
        self.assertTrue(calls["destroyed"])
        self.assertIn(("-topmost", True), calls["attributes"])
        self.assertEqual(kwargs["title"], dialog.DIALOG_TITLE)
        self.assertEqual(kwargs["initialdir"], str(self.folder))
        self.assertEqual(kwargs["filetypes"], BROWSE_FILETYPES)

    def test_cancel_writes_nothing(self):
        code, stdout, calls, _ = self._run("")

        self.assertEqual(code, 0)
        self.assertEqual(stdout, "")
        self.assertTrue(calls["destroyed"])


class ChooseFileTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.folder = Path(self._temp.name)
        self.initial = str(self.folder / "book.xlsx")

    def tearDown(self):
        self._temp.cleanup()

    def _invoke(self, initial=None, **completed_kwargs):
        completed = subprocess.CompletedProcess(args=[], **completed_kwargs)
        with mock.patch("core.dialog.subprocess.run", return_value=completed) as run:
            result = choose_file(self.initial if initial is None else initial)
        return result, run

    def test_returns_selected_path(self):
        result, _ = self._invoke(returncode=0, stdout="/tmp/a.xlsx\n", stderr="")
        self.assertEqual(result, "/tmp/a.xlsx")

    def test_cancel_returns_none(self):
        result, _ = self._invoke(returncode=0, stdout="", stderr="")
        self.assertIsNone(result)

    def test_child_is_launched_in_project_root(self):
        _, run = self._invoke(returncode=0, stdout="", stderr="")

        command = run.call_args.args[0]
        kwargs = run.call_args.kwargs
        self.assertEqual(command[:3], [sys.executable, "-m", "core.dialog"])
        self.assertEqual(command[3], str(self.folder))
        self.assertEqual(kwargs["cwd"], str(PROJECT_ROOT))
        self.assertEqual(kwargs["encoding"], "utf-8")

    def test_blank_initial_uses_home(self):
        _, run = self._invoke(initial="", returncode=0, stdout="", stderr="")
        self.assertEqual(run.call_args.args[0][3], str(Path.home()))

    def test_missing_initial_folder_uses_home(self):
        missing = str(self.folder / "gone" / "book.xlsx")
        _, run = self._invoke(initial=missing, returncode=0, stdout="", stderr="")
        self.assertEqual(run.call_args.args[0][3], str(Path.home()))

    def test_failure_reports_last_stderr_line(self):
        with self.assertRaises(DialogError) as raised:
            self._invoke(
                returncode=1,
                stdout="",
                stderr=(
                    "Traceback (most recent call last):\n"
                    "ModuleNotFoundError: No module named '_tkinter'\n"
                ),
            )
        self.assertEqual(
            str(raised.exception), "ModuleNotFoundError: No module named '_tkinter'"
        )

    def test_failure_without_stderr_reports_exit_code(self):
        with self.assertRaises(DialogError) as raised:
            self._invoke(returncode=-6, stdout="", stderr="")
        self.assertIn("-6", str(raised.exception))

    def test_launch_error_is_wrapped(self):
        with mock.patch("core.dialog.subprocess.run", side_effect=OSError("no exec")):
            with self.assertRaises(DialogError):
                choose_file(self.initial)


if __name__ == "__main__":
    unittest.main()
