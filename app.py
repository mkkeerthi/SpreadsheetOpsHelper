from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from core.adapters import open_workbook
from core.copier import copy_ranges
from core.dialog import DialogError, choose_file
from core.logging_setup import close_run_logger, get_run_logger
from core.numbers_macos import UnsupportedPlatformError
from core.validator import ValidationError, compare_workbooks, parse_ranges

OPTION_MASTER = "Copy to Master File"
OPTION_FINAL = "Copy to Final File"


def _init_state() -> None:
    defaults = {
        "source_path": "",
        "dest_path": "",
        "checked": False,
        "check_signature": None,
        "check_error": None,
        "check_warnings": [],
        "sheet_rows": [],
        "result": None,
        "failure": None,
        "browse_error": None,
        "theme_choice": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _clean_path(value: str | None) -> str:
    return (value or "").strip().strip('"').strip("'")


def _is_dark_theme() -> bool:
    return st.context.theme.type == "dark"


def _request_theme_change() -> None:
    st.session_state["theme_choice"] = st.session_state["dark_theme"]


def _apply_theme(dark: bool | None) -> None:
    """Store the appearance Streamlit reads when the page loads.

    Streamlit resolves the theme in the browser, so a change needs a reload.
    ``dark=None`` keeps the stored choice and only records the light default
    when the browser follows the operating system instead of a fixed theme.
    """
    desired = None if dark is None else ("Dark" if dark else "Light")
    st.html(
        f"""
        <script>
        (() => {{
          const key = `stActiveTheme-${{window.location.pathname}}-v2`;
          const stored = localStorage.getItem(key);
          const desired = {json.dumps(desired)};
          const light = JSON.stringify("Light");
          const darkChoice = JSON.stringify("Dark");
          try {{
            if (desired !== null) {{
              if (stored !== JSON.stringify(desired)) {{
                localStorage.setItem(key, JSON.stringify(desired));
                window.location.reload();
              }}
            }} else if (stored !== light && stored !== darkChoice) {{
              localStorage.setItem(key, light);
              if ({json.dumps(_is_dark_theme())}) window.location.reload();
            }}
          }} catch (error) {{
            console.warn("Could not store the theme preference.", error);
          }}
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def _ask_for_file(initial: str) -> str | None:
    try:
        return choose_file(initial)
    except DialogError as exc:
        st.session_state["browse_error"] = (
            f"Could not open the file dialog ({exc}). Type the path instead."
        )
        return None


def _browse_callback(state_key: str) -> None:
    st.session_state["browse_error"] = None
    chosen = _ask_for_file(st.session_state.get(state_key, ""))
    if chosen:
        st.session_state[state_key] = chosen


def _run_check(source_path: str, destination_path: str) -> None:
    st.session_state["checked"] = False
    st.session_state["check_signature"] = None
    st.session_state["check_error"] = None
    st.session_state["check_warnings"] = []
    st.session_state["sheet_rows"] = []
    st.session_state["result"] = None
    st.session_state["failure"] = None

    source_path = _clean_path(source_path)
    destination_path = _clean_path(destination_path)
    if not source_path or not destination_path:
        st.session_state["check_error"] = (
            "Select both a source document and a destination document."
        )
        return
    if Path(source_path).resolve() == Path(destination_path).resolve():
        st.session_state["check_error"] = (
            "Source and destination must be different files."
        )
        return

    source = None
    destination = None
    try:
        source = open_workbook(source_path)
        destination = open_workbook(destination_path)
        report = compare_workbooks(source, destination)

        rows = [
            {
                "sheet": name,
                "columns": source.max_column(name),
                "last_source_row": source.last_data_row(name),
                "append_row": destination.last_data_row(name) + 1,
            }
            for name in source.sheet_names()
        ]

        if report.errors:
            st.session_state["check_error"] = " ".join(report.errors)
            return

        st.session_state["sheet_rows"] = rows
        st.session_state["check_warnings"] = list(report.warnings)
        st.session_state["check_signature"] = (source_path, destination_path)
        st.session_state["checked"] = True
    except UnsupportedPlatformError as exc:
        st.session_state["check_error"] = str(exc)
    except Exception as exc:
        st.session_state["check_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if source is not None:
            source.close()
        if destination is not None:
            destination.close()


def _run_submit(progress_slot) -> None:
    st.session_state["result"] = None
    st.session_state["failure"] = None

    source_path = _clean_path(st.session_state.get("source_path"))
    destination_path = _clean_path(st.session_state.get("dest_path"))
    signature = st.session_state.get("check_signature")

    if not st.session_state.get("checked") or signature != (
        source_path,
        destination_path,
    ):
        st.session_state["failure"] = {
            "message": "Files changed since the last Check File. Click Check File again.",
            "log_path": None,
            "kind": "stale",
        }
        return

    entries = [
        (
            info["sheet"],
            st.session_state.get(f"start_{info['sheet']}", ""),
            st.session_state.get(f"end_{info['sheet']}", ""),
        )
        for info in st.session_state["sheet_rows"]
    ]

    source = None
    destination = None
    logger = None
    log_path = None
    progress = progress_slot.progress(0.0, text="Preparing...")

    try:
        source = open_workbook(source_path)
        ranges = parse_ranges(entries, source)
        if not ranges:
            raise ValidationError("Enter a row range for at least one sheet.")

        logger, log_path = get_run_logger()
        logger.info("Copy started: source=%s destination=%s", source_path, destination_path)
        logger.info("Ranges: %s", ranges)

        destination = open_workbook(destination_path)
        results = copy_ranges(
            source,
            destination,
            ranges,
            on_progress=lambda done, total: progress.progress(
                min(done / total, 1.0), text=f"Copying {done} of {total} rows..."
            ),
            logger=logger,
        )

        progress.progress(1.0, text="Saving timestamped copy...")
        output_path = destination.save_copy()
        logger.info("Output written to %s", output_path)
        progress.empty()
        st.session_state["result"] = {
            "results": results,
            "output": str(output_path),
        }
    except ValidationError as exc:
        progress.empty()
        st.session_state["failure"] = {
            "message": str(exc),
            "log_path": None,
            "kind": "validation",
        }
    except UnsupportedPlatformError as exc:
        progress.empty()
        if logger is not None:
            logger.exception("Unsupported platform")
        st.session_state["failure"] = {
            "message": str(exc),
            "log_path": str(log_path) if log_path else None,
            "kind": "runtime",
        }
    except Exception as exc:
        progress.empty()
        if logger is not None:
            logger.exception("Copy failed")
        st.session_state["failure"] = {
            "message": f"{type(exc).__name__}: {exc}",
            "log_path": str(log_path) if log_path else None,
            "kind": "runtime",
        }
    finally:
        if source is not None:
            source.close()
        if destination is not None:
            destination.close()
        if logger is not None:
            close_run_logger(logger)


def _render_results() -> None:
    result = st.session_state.get("result")
    failure = st.session_state.get("failure")

    if result:
        parts = [
            f"{item.copied_rows} rows from {item.sheet}"
            for item in result["results"]
            if item.copied_rows
        ]
        if parts:
            st.success("Copied " + ", ".join(parts))
        else:
            st.warning("No rows were copied. The selected source rows were blank.")

        for item in result["results"]:
            if item.copied_rows:
                st.caption(
                    f"{item.sheet}: destination rows "
                    f"{item.destination_start_row}-{item.destination_end_row}"
                )
            if item.skipped_rows:
                st.caption(
                    f"{item.sheet}: skipped {item.skipped_rows} blank source row(s)"
                )

        st.caption("Original destination file was not modified. New file:")
        st.code(result["output"], language=None)

    if failure:
        if failure.get("kind") == "runtime":
            st.error("Failed copying. Check logs for more information.")
            with st.expander("Failure details"):
                st.write(failure["message"])
                if failure.get("log_path"):
                    st.code(failure["log_path"], language=None)
        else:
            st.error(failure["message"])


st.set_page_config(page_title="Numbers Work Helper", layout="wide")
_init_state()

title_column, theme_column = st.columns([5, 1], vertical_alignment="center")
title_column.title("Numbers Work Helper")
theme_column.toggle(
    "Dark theme",
    value=_is_dark_theme(),
    key="dark_theme",
    on_change=_request_theme_change,
    help="Switch between the light and dark colour theme.",
)

with st.container(border=True):
    st.subheader("Action")
    mode = st.radio(
        "Action",
        [OPTION_MASTER, OPTION_FINAL],
        index=0,
        label_visibility="collapsed",
    )
    is_final = mode == OPTION_FINAL
    if is_final:
        st.info("Option 2 is not implemented yet. Select 'Copy to Master File' to continue.")

with st.container(border=True):
    st.subheader("Input")

    if st.session_state.get("browse_error"):
        st.warning(st.session_state["browse_error"])

    source_button, source_box = st.columns([1, 8])
    source_button.button(
        "Browse",
        key="browse_source",
        on_click=_browse_callback,
        args=("source_path",),
        disabled=is_final,
    )
    source_box.text_input(
        "Source document",
        key="source_path",
        placeholder="Source Document",
        label_visibility="collapsed",
        disabled=is_final,
    )

    destination_button, destination_box = st.columns([1, 8])
    destination_button.button(
        "Browse",
        key="browse_destination",
        on_click=_browse_callback,
        args=("dest_path",),
        disabled=is_final,
    )
    destination_box.text_input(
        "Destination document",
        key="dest_path",
        placeholder="Destination Document",
        label_visibility="collapsed",
        disabled=is_final,
    )

    _, check_button = st.columns([8, 1])
    check_clicked = check_button.button(
        "Check File", key="check_file", type="primary", disabled=is_final
    )
    if check_clicked:
        _run_check(st.session_state.get("source_path"), st.session_state.get("dest_path"))

    if st.session_state.get("check_error"):
        st.error(st.session_state["check_error"])
    for warning in st.session_state.get("check_warnings", []):
        st.warning(warning)

    submit_clicked = False
    if st.session_state.get("checked") and not is_final:
        st.markdown(
            "Enter the source row range for each sheet. "
            "Leave both boxes blank to skip a sheet."
        )
        for info in st.session_state["sheet_rows"]:
            sheet = info["sheet"]
            name_column, start_column, end_column = st.columns([1.3, 2, 2])
            name_column.markdown(f"**{sheet}**")
            if info["last_source_row"]:
                name_column.caption(
                    f"Source rows 1-{info['last_source_row']}; "
                    f"adding to destination from row {info['append_row']}"
                )
            else:
                name_column.caption("No data rows found in this source sheet")
            start_column.text_input(
                "Starting Row Number",
                key=f"start_{sheet}",
                placeholder="Starting Row Number",
                label_visibility="collapsed",
            )
            end_column.text_input(
                "Ending Row Number",
                key=f"end_{sheet}",
                placeholder="Ending Row Number",
                label_visibility="collapsed",
            )

        _, submit_button = st.columns([8, 1])
        submit_clicked = submit_button.button(
            "Submit", key="submit", type="primary", disabled=is_final
        )

with st.container(border=True):
    st.subheader("Output")
    progress_slot = st.empty()
    if submit_clicked:
        _run_submit(progress_slot)
    _render_results()

theme_choice = st.session_state.get("theme_choice")
st.session_state["theme_choice"] = None
_apply_theme(theme_choice)
