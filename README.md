# Numbers Work Helper

A single-screen Streamlit tool for copying row ranges from a source spreadsheet into the matching sheets of a destination spreadsheet. The original destination file is never modified: each run writes a new timestamped copy beside it.

## Quick start (macOS)

If Python 3.10+ with Tkinter is already installed:

```bash
cd /path/to/NumbersWorkHelper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501 (Streamlit normally opens it for you). Press `Ctrl+C` in the terminal to stop the app.

The sections below cover installing the prerequisites, granting the macOS permissions the app needs, and fixing common setup errors.

## Prerequisites (macOS)

| Requirement | Details |
|---|---|
| macOS | macOS 12 Monterey or later recommended. Apple Silicon and Intel are both supported. |
| Python | 3.10 or newer; 3.12 or 3.13 recommended. Verify with `python3 --version`. |
| Tkinter | Required for the **Browse** file picker. Included with the python.org installer; Homebrew needs the matching `python-tk` package. |
| pip and venv | Included with Python. Dependencies are installed into a project-local virtual environment. |
| Apple Numbers | Optional. Only needed to read or write `.numbers` files. Free from the Mac App Store. |
| Disk space | Several hundred MB for the virtual environment and Streamlit's dependencies. |
| Network | Needed once, to download the Python installer and pip packages. |

No `sudo` is needed to install the app itself. Do not install the Python packages globally; use the virtual environment below.

### 1. Install Python and Tkinter

#### Option A: python.org installer (recommended)

The official installer bundles Tcl/Tk, so the **Browse** buttons work without extra steps.

1. Open https://www.python.org/downloads/macos/ and download the latest macOS 64-bit universal2 installer for Python 3.12 or 3.13.
2. Run the `.pkg` and complete the installer with the default options.
3. Open a new Terminal window and verify both Python and Tkinter:

```bash
python3 --version
python3 -c "import tkinter; print('Tk', tkinter.TkVersion)"
```

Both commands should succeed. The second prints a Tk version such as `Tk 8.6`.

#### Option B: Homebrew

Homebrew's Python does not include Tkinter. Install a matching `python-tk` package as well.

1. Install Homebrew if it is not already installed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. Follow the PATH instructions Homebrew prints at the end. On Apple Silicon that is usually:

```bash
eval "$(/opt/homebrew/bin/brew shellenv)"
```

The Homebrew installer may prompt to install the Xcode Command Line Tools. Accept it; if it does not, run:

```bash
xcode-select --install
```

3. Install Python and the Tk package that matches its minor version:

```bash
brew install python
python3 --version          # for example, Python 3.13.x
brew install python-tk@3.13
```

If `python3 --version` reports 3.12, use `python-tk@3.12` instead. The versions must match.

4. Verify the interpreter and Tkinter:

```bash
which python3
python3 -c "import tkinter; print('Tk', tkinter.TkVersion)"
```

`which python3` should point to Homebrew or the python.org install, not `/usr/bin/python3`.

> If you use pyenv, conda, or another Python manager, make sure that interpreter can `import tkinter` before continuing. The simplest path on macOS is the python.org installer.

### 2. Create the virtual environment and install dependencies

From the project folder:

```bash
cd /path/to/NumbersWorkHelper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The prompt should now start with `(.venv)`. Every new Terminal session needs `source .venv/bin/activate` before running the app again.

`requirements.txt` installs:

- `streamlit>=1.40` (tested with 1.66.1)
- `openpyxl>=3.1` (tested with 3.1.5)

The virtual environment also prevents macOS and Homebrew Python from rejecting global installs with an `externally-managed-environment` error.

### 3. Grant macOS permissions

#### File browser (Browse buttons)

The first time you use **Browse**, macOS may ask for access to Desktop, Documents, or Downloads. Allow it for the application you started Streamlit from (Terminal, iTerm2, or VS Code).

If no prompt appears and the file picker cannot see a folder:

1. Open **System Settings → Privacy & Security → Files and Folders**.
2. Enable the relevant folders for Terminal (or your terminal/IDE app).
3. For files in iCloud Drive, an external volume, or another protected location, add the same app under **Full Disk Access** instead.
4. Quit and reopen the terminal app, then restart Streamlit.

If you run Streamlit on a headless Mac over SSH, there is no graphical file dialog. Type the file paths into the text boxes instead of using **Browse**.

#### Apple Numbers (`.numbers` files only)

1. Install **Numbers** from the Mac App Store and open it once.
2. The first `.numbers` operation triggers an Automation prompt such as *"Terminal wants to control Numbers."* Click **OK**.
3. If the prompt was dismissed, enable it manually under **System Settings → Privacy & Security → Automation** → select your terminal or IDE app → enable **Numbers**.
4. Restart Streamlit after changing the permission.

As a last resort, reset only that app's automation approvals and try again:

```bash
tccutil reset AppleEvents com.apple.Terminal
```

Use `com.googlecode.iterm2` for iTerm2 or `com.microsoft.VSCode` for VS Code. This clears the selected app's automation approvals, so the prompt will appear again.

The app exports the `.numbers` file to a temporary `.xlsx`, performs the copy, then asks Numbers to save a new timestamped `.numbers` file. Keep Numbers available and avoid dismissing its dialogs (for example, "document is in use") while a copy is running. The original file is never modified.

### 4. Run the app

With the virtual environment active:

```bash
cd /path/to/NumbersWorkHelper
source .venv/bin/activate
python -m streamlit run app.py
```

Open http://localhost:8501 if the browser does not open automatically.

Useful options:

```bash
# Use a different port if 8501 is already taken
python -m streamlit run app.py --server.port 8502

# Start without opening a browser
python -m streamlit run app.py --server.headless true
```

Stopping the app with `Ctrl+C` frees the port. If macOS asks whether to allow incoming network connections for Python, local use only needs the app to listen on localhost; allowing or denying the firewall prompt does not affect local access.

## Troubleshooting (macOS)

| Symptom | Fix |
|---|---|
| `zsh: command not found: python3` | Install Python from python.org or Homebrew. For Homebrew, follow the `brew shellenv` instructions and open a new Terminal. |
| `which python3` shows `/usr/bin/python3` | The macOS stub is being used instead of your install. Fix `PATH` (Homebrew `shellenv`) or use the full path to the python.org interpreter. |
| `No module named streamlit` | The virtual environment is not active. Run `source .venv/bin/activate`, then `python -m pip install -r requirements.txt`. |
| `ModuleNotFoundError: No module named '_tkinter'` or Browse does nothing | Tkinter is missing. Install `python-tk@X.Y` matching `python3 --version`, or reinstall Python from python.org. You can still type file paths manually. |
| `externally-managed-environment` from pip | You are outside the virtual environment. Run `source .venv/bin/activate` and install again. |
| `Address already in use` | Another Streamlit instance is running. Stop it or add `--server.port 8502`. |
| Browser does not open | Visit http://localhost:8501 manually. |
| `Operation not permitted` when reading or writing a file | Grant **Files and Folders** or **Full Disk Access** to Terminal in System Settings, or move the files to your home folder. |
| AppleScript error `-1743` / "not authorized to send Apple events" | Automation permission is missing. Enable Numbers under **Privacy & Security → Automation**, then restart the terminal and Streamlit. |
| Numbers export hangs or fails | Close the document in Numbers, update macOS and Numbers, or export the file to `.xlsx` manually and use that instead. Very large `.numbers` files can exceed the 5-minute AppleScript timeout. |
| `OSError: [Errno 24] Too many open files` | Raise the limit before starting: `ulimit -n 10240`. |
| `Source and destination must be different files.` | Select two different files. |

## Windows setup

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

`.numbers` files are not supported on Windows; export them to `.xlsx` or `.csv` first.

## How to use

1. **Action** — choose `Copy to Master File`. (`Copy to Final File` is a placeholder and is not implemented.)
2. **Input** — click **Browse** for the source and destination files, or type their paths. Click **Check File**.
3. For each sheet shown, enter the source **starting** and **ending** row numbers. Leave both boxes blank to skip that sheet.
4. Click **Submit**. The **Output** section shows progress, then the per-sheet row counts and the new file path.

Row numbers are absolute spreadsheet rows. In the sample files the headers are on row 5 and data runs from row 7, so enter `7` and `14`.

## Copy rules

- Copied rows are appended after the last non-blank row in each destination sheet. Formatting-only blank rows are ignored.
- Blank and null source cells are skipped and write nothing.
- Each written cell keeps the source cell's number format (for example `mm-dd-yy` or `0.00`). Fonts, fills, borders, alignment, and column widths are not copied.
- A source row is counted only when at least one value was actually written. Fully blank rows are skipped.
- Sheet count, sheet names, and per-sheet column counts must match between the two files.

## Supported files

| Format | Read | Write |
|---|---|---|
| `.xlsx` / `.xlsm` | Yes | Yes |
| `.csv` | Yes (treated as one sheet named `Sheet1`) | Yes |
| `.numbers` | macOS only, via the Numbers app | macOS only, new `.numbers` file |
| `.xls` | No — save as `.xlsx` first | No |

Apple Numbers files are exported and saved through AppleScript. See [Grant macOS permissions](#3-grant-macos-permissions). On Windows this is unavailable; export the document to `.xlsx` or `.csv` first.

`openpyxl` writes xlsx/xlsm files but does not preserve charts, images, or other embedded objects. VBA is retained for `.xlsm` files.

## Output files and logs

- Successful runs create `<original name>_<YYYYMMDD_HHMMSS>.<ext>` beside the destination file. If that name already exists, a `_1`, `_2`, ... suffix is added. The original file is never written, backed up, or overwritten.
- Runtime failures are written to `logs/copy_<YYYYMMDD_HHMMSS>.log` with a full timestamped stack trace, and no output file is left behind.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Project layout

```
app.py                  Streamlit UI (Action, Input, Output)
core/adapters.py        Format dispatch and supported extensions
core/workbook.py        xlsx/csv read, last-data-row detection, timestamped save
core/validator.py       Sheet/column checks and row-range parsing
core/copier.py          Row copy engine and per-sheet counts
core/logging_setup.py   Timestamped log files under logs/
core/numbers_macos.py   AppleScript bridge for .numbers files
tests/                  Unit tests for validation, copying, and CSV handling
```

## Current limitations

- Option 2 (`Copy to Final File`) is intentionally not implemented.
- There is no column mapping, header rewriting, deduplication, or undo.
- `.numbers` support requires macOS with Numbers installed and cannot be exercised on Windows.
