"""
Lyceum Test Runner
------------------
Students run this file once per session.
They never need to edit it.

Usage:
    python StationLyceum.py

Folder layout expected next to this file:
    weeks/          <- teacher drops weekN.py files here
    submissions/    <- student puts their work here
    results.json    <- auto-created, stores last run results
"""

import tkinter as tk
import importlib.util
import importlib
import sys
import json
import traceback
import threading
from pathlib import Path
from datetime import datetime

# ── paths ────────────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent.resolve()
WEEKS_DIR   = BASE_DIR / "weeks"
SUBMIT_DIR  = BASE_DIR / "submissions"
RESULTS_FILE = BASE_DIR / "results.json"

for d in (WEEKS_DIR, SUBMIT_DIR):
    d.mkdir(exist_ok=True)

# ── colour palette ────────────────────────────────────────────────────────────

C = {
    "bg":           "#0d1117",
    "panel":        "#161b22",
    "border":       "#21262d",
    "accent":       "#3fb950",   # green
    "accent_dim":   "#238636",
    "warn":         "#d29922",
    "danger":       "#f85149",
    "info":         "#58a6ff",
    "muted":        "#484f58",
    "text":         "#c9d1d9",
    "text_bright":  "#f0f6fc",
    "text_dim":     "#6e7681",
    "tab_active":   "#1f2937",
    "tab_hover":    "#161b22",
    "pass_bg":      "#0d1117",
    "fail_bg":      "#0d1117",
    "story":        "#79c0ff",
}

FONTS = {
    "mono":    ("Courier New", 11),
    "mono_sm": ("Courier New", 10),
    "ui":      ("Helvetica", 11),
    "ui_sm":   ("Helvetica", 10),
    "ui_lg":   ("Helvetica", 13, "bold"),
    "title":   ("Helvetica", 16, "bold"),
    "label":   ("Helvetica", 9),
}

# ── week file loader ──────────────────────────────────────────────────────────

def is_valid_week_file(path: Path) -> bool:
    """
    Light validation: file must be a .py, named week*.py,
    and must define WEEK_META dict when imported.
    """
    if not path.suffix == ".py":
        return False
    if not path.stem.startswith("week"):
        return False
    return True


def load_week_module(path: Path):
    """Import a week file as a module. Returns module or raises."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def discover_weeks() -> list[dict]:
    """
    Scan weeks/ folder, load valid week files.
    Returns list of week descriptors sorted by week number.
    Each descriptor: { path, module, meta }
    """
    found = []
    if not WEEKS_DIR.exists():
        return found

    for p in sorted(WEEKS_DIR.glob("week*.py")):
        if not is_valid_week_file(p):
            continue
        try:
            mod  = load_week_module(p)
            meta = getattr(mod, "WEEK_META", None)
            if meta is None or not isinstance(meta, dict):
                continue
            found.append({"path": p, "module": mod, "meta": meta})
        except Exception as e:
            # show broken week as error tab later
            found.append({"path": p, "module": None, "meta": None, "error": str(e)})

    return found

# ── test runner logic ─────────────────────────────────────────────────────────

def run_week_tests(week: dict) -> list[dict]:
    """
    Execute all challenges in a week against the student's submission.
    Returns list of challenge result dicts.
    """
    meta       = week["meta"]
    mod        = week["module"]
    submit_name = meta.get("submission_file", "unknown.py")
    submit_path = SUBMIT_DIR / submit_name

    challenges = getattr(mod, "CHALLENGES", [])
    results    = []

    # load student module once
    student_mod  = None
    load_error   = None

    if not submit_path.exists():
        load_error = f"File not found: submissions/{submit_name}\nMake sure your file is named exactly '{submit_name}' and is inside the 'submissions' folder."
    else:
        try:
            spec = importlib.util.spec_from_file_location("student_work", submit_path)
            student_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(student_mod)
        except Exception as e:
            load_error = f"Could not load {submit_name}:\n{traceback.format_exc()}"

    for ch in challenges:
        ch_result = {
            "id":       ch.get("id", "?"),
            "title":    ch.get("title", "Unnamed"),
            "mission":  ch.get("mission", ""),
            "tests":    [],
            "passed":   0,
            "total":    0,
            "story_pass": ch.get("story_pass", ""),
            "load_error": load_error,
        }

        if load_error:
            results.append(ch_result)
            continue

        for test in ch.get("tests", []):
            t_result = {
                "call":     test.get("call", ""),
                "note":     test.get("note", ""),
                "passed":   False,
                "got":      None,
                "expected": test.get("expected"),
                "error":    None,
            }

            func_name = test.get("func")
            args      = test.get("args", [])
            expected  = test.get("expected")

            func = getattr(student_mod, func_name, None)
            if func is None:
                t_result["error"] = f"function '{func_name}' not found in {submit_name}"
            else:
                try:
                    # capture prints if this is a print test
                    if test.get("is_print_test"):
                        import io
                        buf = io.StringIO()
                        old = sys.stdout
                        sys.stdout = buf
                        try:
                            func(*args)
                        finally:
                            sys.stdout = old
                        printed = buf.getvalue().strip().splitlines()
                        t_result["got"] = printed
                        t_result["passed"] = (printed == expected)
                    else:
                        got = func(*args)
                        t_result["got"]    = got
                        t_result["passed"] = (got == expected)
                except Exception as e:
                    t_result["error"] = traceback.format_exc(limit=3)

            ch_result["tests"].append(t_result)
            ch_result["total"] += 1
            if t_result["passed"]:
                ch_result["passed"] += 1

        results.append(ch_result)

    return results

# ── results persistence ───────────────────────────────────────────────────────

def load_results() -> dict:
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_results(all_results: dict):
    RESULTS_FILE.write_text(json.dumps(all_results, indent=2, default=str))

# ── GUI ───────────────────────────────────────────────────────────────────────

class LyceumRunner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Station Lyceum — Test Runner")
        self.configure(bg=C["bg"])
        self.geometry("920x780")
        self.minsize(760, 520)

        self.weeks        = []
        self.current_week = None
        self.all_results  = load_results()
        self.tab_buttons  = []

        self._build_ui()
        self._refresh_weeks()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # top bar
        top = tk.Frame(self, bg=C["panel"], height=52)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        tk.Label(
            top, text="STATION LYCEUM",
            bg=C["panel"], fg=C["accent"],
            font=("Helvetica", 14, "bold"),
            padx=18,
        ).pack(side="left", pady=12)

        self.status_lbl = tk.Label(
            top, text="● ready",
            bg=C["panel"], fg=C["accent"],
            font=FONTS["ui_sm"],
        )
        self.status_lbl.pack(side="left", pady=12)

        self.refresh_btn = tk.Button(
            top, text="↺  Refresh weeks",
            bg=C["panel"], fg=C["text_dim"],
            activebackground=C["border"], activeforeground=C["text"],
            relief="flat", cursor="hand2",
            font=FONTS["ui_sm"],
            command=self._refresh_weeks,
            padx=12,
        )
        self.refresh_btn.pack(side="right", pady=10, padx=12)

        # divider
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        # tab row
        self.tab_row = tk.Frame(self, bg=C["panel"])
        self.tab_row.pack(fill="x")
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        # body
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True)

        # left: challenge list
        self.left_panel = tk.Frame(body, bg=C["panel"], width=220)
        self.left_panel.pack(fill="y", side="left")
        self.left_panel.pack_propagate(False)

        tk.Frame(body, bg=C["border"], width=1).pack(fill="y", side="left")

        # right: detail
        right = tk.Frame(body, bg=C["bg"])
        right.pack(fill="both", expand=True, side="left")

        # -- right top: mission brief + run button
        brief_bar = tk.Frame(right, bg=C["panel"], height=90)
        brief_bar.pack(fill="x")
        brief_bar.pack_propagate(False)

        brief_inner = tk.Frame(brief_bar, bg=C["panel"])
        brief_inner.pack(fill="both", expand=True, padx=16, pady=10)

        self.mission_lbl = tk.Label(
            brief_inner, text="SELECT A WEEK TO BEGIN",
            bg=C["panel"], fg=C["warn"],
            font=("Helvetica", 9, "bold"),
            anchor="w",
        )
        self.mission_lbl.pack(fill="x")

        self.brief_lbl = tk.Label(
            brief_inner, text="No week loaded. Drop a week file into the 'weeks' folder and click Refresh.",
            bg=C["panel"], fg=C["text_dim"],
            font=FONTS["ui_sm"],
            anchor="w", wraplength=600, justify="left",
        )
        self.brief_lbl.pack(fill="x", pady=(3, 0))

        tk.Frame(right, bg=C["border"], height=1).pack(fill="x")

        # -- right mid: output scroll
        out_frame = tk.Frame(right, bg=C["bg"])
        out_frame.pack(fill="both", expand=True)

        out_label = tk.Frame(out_frame, bg=C["panel"])
        out_label.pack(fill="x")
        tk.Label(
            out_label, text="STATION OUTPUT",
            bg=C["panel"], fg=C["text_dim"],
            font=("Helvetica", 8, "bold"),
            padx=16, pady=5,
            anchor="w",
        ).pack(side="left")

        self.timestamp_lbl = tk.Label(
            out_label, text="",
            bg=C["panel"], fg=C["muted"],
            font=FONTS["label"],
            padx=16,
        )
        self.timestamp_lbl.pack(side="right")
        tk.Frame(right, bg=C["border"], height=1).pack(fill="x")

        self.output_text = tk.Text(
            out_frame,
            bg=C["bg"], fg=C["text"],
            font=FONTS["mono"],
            relief="flat",
            padx=16, pady=12,
            wrap="word",
            state="disabled",
            cursor="arrow",
        )
        self.output_text.pack(fill="both", expand=True, side="left")

        scrollbar = tk.Scrollbar(out_frame, command=self.output_text.yview, bg=C["panel"])
        scrollbar.pack(fill="y", side="right")
        self.output_text.config(yscrollcommand=scrollbar.set)

        # text tags
        self.output_text.tag_config("system",  foreground=C["text_dim"])
        self.output_text.tag_config("pass",    foreground=C["accent"])
        self.output_text.tag_config("fail",    foreground=C["danger"])
        self.output_text.tag_config("warn",    foreground=C["warn"])
        self.output_text.tag_config("info",    foreground=C["info"])
        self.output_text.tag_config("story",   foreground=C["story"])
        self.output_text.tag_config("error",   foreground=C["danger"])
        self.output_text.tag_config("bright",  foreground=C["text_bright"])
        self.output_text.tag_config("muted",   foreground=C["text_dim"])
        self.output_text.tag_config("heading", foreground=C["accent"], font=("Helvetica", 10, "bold"))

        # -- run button bar
        run_bar = tk.Frame(right, bg=C["panel"], height=52)
        run_bar.pack(fill="x", side="bottom")
        run_bar.pack_propagate(False)
        tk.Frame(right, bg=C["border"], height=1).pack(fill="x", side="bottom")

        self.run_btn = tk.Button(
            run_bar,
            text="▶   RUN TESTS",
            bg=C["accent_dim"], fg=C["text_bright"],
            activebackground=C["accent"], activeforeground=C["bg"],
            relief="flat", cursor="hand2",
            font=("Helvetica", 12, "bold"),
            padx=28, pady=0,
            command=self._run_tests,
        )
        self.run_btn.pack(side="left", padx=16, pady=10)

        self.progress_lbl = tk.Label(
            run_bar, text="",
            bg=C["panel"], fg=C["text_dim"],
            font=FONTS["ui_sm"],
        )
        self.progress_lbl.pack(side="left", pady=10)

        self.clear_btn = tk.Button(
            run_bar,
            text="Clear output",
            bg=C["panel"], fg=C["text_dim"],
            activebackground=C["border"], activeforeground=C["text"],
            relief="flat", cursor="hand2",
            font=FONTS["ui_sm"],
            command=self._clear_output,
        )
        self.clear_btn.pack(side="right", padx=16, pady=10)

    # ── tab management ─────────────────────────────────────────────────────────

    def _refresh_weeks(self):
        # clear old tabs
        for w in self.tab_row.winfo_children():
            w.destroy()
        self.tab_buttons = []

        self.weeks = discover_weeks()

        if not self.weeks:
            tk.Label(
                self.tab_row,
                text="  No week files found in weeks/ folder",
                bg=C["panel"], fg=C["text_dim"],
                font=FONTS["ui_sm"],
                padx=12, pady=10,
            ).pack(side="left")
            self._set_status("no weeks loaded", C["warn"])
            return

        for i, week in enumerate(self.weeks):
            meta  = week["meta"]
            label = meta.get("tab_label", week["path"].stem) if meta else week["path"].stem
            err   = week.get("error")
            color = C["danger"] if err else C["text_dim"]

            btn = tk.Button(
                self.tab_row,
                text=label,
                bg=C["panel"], fg=color,
                activebackground=C["tab_active"],
                activeforeground=C["text"],
                relief="flat", cursor="hand2",
                font=FONTS["ui"],
                padx=16, pady=10,
                command=lambda idx=i: self._select_week(idx),
            )
            btn.pack(side="left")
            self.tab_buttons.append(btn)

        # select first week by default
        self._select_week(0)
        self._set_status(f"{len(self.weeks)} week(s) loaded", C["accent"])

    def _select_week(self, idx: int):
        self.current_week = idx

        # update tab highlight
        for i, btn in enumerate(self.tab_buttons):
            if i == idx:
                btn.config(bg=C["tab_active"], fg=C["text_bright"],
                           font=("Helvetica", 11, "bold"))
            else:
                btn.config(bg=C["panel"], fg=C["text_dim"],
                           font=FONTS["ui"])

        week = self.weeks[idx]
        if week.get("error"):
            self._set_brief("LOAD ERROR", week["error"])
            self._rebuild_challenge_list([])
            return

        meta = week["meta"]
        self._set_brief(
            meta.get("tab_label", "").upper(),
            meta.get("description", "")
        )
        self._rebuild_challenge_list(getattr(week["module"], "CHALLENGES", []))

        # restore saved results if any
        week_key = week["path"].stem
        if week_key in self.all_results:
            self._display_saved_results(week_key)
        else:
            self._clear_output()
            self._print("system", f"[ {meta.get('title', week['path'].stem)} ]")
            self._print("system",  "  Press  ▶ RUN TESTS  to test your submission.")
            submit = meta.get("submission_file", "?")
            self._print("muted",  f"  Expected file: submissions/{submit}")

        self._update_progress(week_key)

    def _rebuild_challenge_list(self, challenges: list):
        for w in self.left_panel.winfo_children():
            w.destroy()

        tk.Label(
            self.left_panel,
            text="CHALLENGES",
            bg=C["panel"], fg=C["text_dim"],
            font=("Helvetica", 8, "bold"),
            anchor="w", padx=14, pady=8,
        ).pack(fill="x")

        tk.Frame(self.left_panel, bg=C["border"], height=1).pack(fill="x")

        if not challenges:
            tk.Label(
                self.left_panel,
                text="No challenges",
                bg=C["panel"], fg=C["muted"],
                font=FONTS["ui_sm"],
                padx=14, pady=10,
            ).pack(fill="x")
            return

        week_key = self.weeks[self.current_week]["path"].stem if self.current_week is not None else None
        saved    = self.all_results.get(week_key, {}).get("challenges", {}) if week_key else {}

        self.ch_frames = {}
        for ch in challenges:
            ch_id = ch.get("id", ch.get("title", "?"))
            ch_saved = saved.get(ch_id, {})
            passed = ch_saved.get("passed", 0)
            total  = ch_saved.get("total", 0)

            if total == 0:
                dot_color = C["muted"]
                status_txt = "not run"
            elif passed == total:
                dot_color = C["accent"]
                status_txt = f"✓  {passed}/{total}"
            else:
                dot_color = C["danger"]
                status_txt = f"✗  {passed}/{total}"

            row = tk.Frame(self.left_panel, bg=C["panel"])
            row.pack(fill="x")

            tk.Frame(row, bg=dot_color, width=3).pack(fill="y", side="left")

            inner = tk.Frame(row, bg=C["panel"])
            inner.pack(fill="x", padx=12, pady=8)

            tk.Label(
                inner,
                text=ch.get("title", "Unnamed"),
                bg=C["panel"], fg=C["text"],
                font=FONTS["ui_sm"],
                anchor="w",
            ).pack(fill="x")

            tk.Label(
                inner,
                text=status_txt,
                bg=C["panel"], fg=dot_color,
                font=("Helvetica", 9),
                anchor="w",
            ).pack(fill="x")

            tk.Frame(self.left_panel, bg=C["border"], height=1).pack(fill="x")
            self.ch_frames[ch_id] = row

    # ── running tests ─────────────────────────────────────────────────────────

    def _run_tests(self):
        if self.current_week is None:
            return

        week = self.weeks[self.current_week]
        if week.get("error"):
            return

        self.run_btn.config(state="disabled", text="  Running…")
        self._set_status("running tests…", C["warn"])
        self._clear_output()

        def worker():
            results = run_week_tests(week)
            self.after(0, lambda: self._display_results(week, results))

        threading.Thread(target=worker, daemon=True).start()

    def _display_results(self, week: dict, results: list):
        meta     = week["meta"]
        week_key = week["path"].stem
        now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.timestamp_lbl.config(text=f"last run: {now}")

        total_ch  = len(results)
        passed_ch = 0

        self._print("heading", f"\n  {meta.get('title', week_key).upper()}")
        self._print("system",  f"  {now}\n")

        ch_saved = {}

        for ch in results:
            load_err = ch.get("load_error")

            self._print("bright", f"  ── {ch['mission'] or ch['title']} ──")

            if load_err:
                self._print("fail",  f"\n  ✗  {ch['title']}")
                self._print("error", f"  {load_err}\n")
                continue

            all_pass = ch["passed"] == ch["total"] and ch["total"] > 0
            ch_color = "pass" if all_pass else "fail"
            ch_icon  = "✓" if all_pass else "✗"

            for t in ch["tests"]:
                if t["error"]:
                    self._print("fail",  f"  ✗  {t['call']}")
                    # show just the last line of the traceback to keep it tidy
                    err_lines = t["error"].strip().splitlines()
                    self._print("error", f"     {err_lines[-1]}")
                elif t["passed"]:
                    note = f"  ({t['note']})" if t["note"] else ""
                    self._print("pass",  f"  ✓  {t['call']} → {repr(t['got'])}{note}")
                else:
                    self._print("fail",  f"  ✗  {t['call']}")
                    self._print("muted", f"     expected: {repr(t['expected'])}")
                    self._print("muted", f"     got:      {repr(t['got'])}")

            summary = f"  {ch_icon}  {ch['title']}  —  {ch['passed']}/{ch['total']} tests passed"
            self._print(ch_color, summary)

            if all_pass and ch.get("story_pass"):
                self._print("story", f"\n  {ch['story_pass']}")
                passed_ch += 1

            self._print("system", "")

            ch_saved[ch["id"]] = {
                "passed": ch["passed"],
                "total":  ch["total"],
            }

        # overall summary
        self._print("system", "  " + "─" * 50)
        if passed_ch == total_ch and total_ch > 0:
            self._print("pass",  f"\n  ALL CHALLENGES PASSED  ({passed_ch}/{total_ch})\n")
        else:
            self._print("warn",  f"\n  {passed_ch}/{total_ch} challenges fully passed\n")

        # save to results.json
        self.all_results[week_key] = {
            "timestamp":  now,
            "passed":     passed_ch,
            "total":      total_ch,
            "challenges": ch_saved,
        }
        save_results(self.all_results)

        # refresh sidebar
        self._rebuild_challenge_list(getattr(week["module"], "CHALLENGES", []))
        self._update_progress(week_key)

        self.run_btn.config(state="normal", text="▶   RUN TESTS")
        status_color = C["accent"] if passed_ch == total_ch else C["warn"]
        self._set_status(f"{passed_ch}/{total_ch} challenges passed", status_color)

    def _display_saved_results(self, week_key: str):
        saved = self.all_results.get(week_key, {})
        ts    = saved.get("timestamp", "unknown")
        p     = saved.get("passed", 0)
        t     = saved.get("total",  0)
        self._clear_output()
        self._print("system", f"  Last run: {ts}")
        self._print("system",  "  Results loaded from results.json\n")
        color = "pass" if p == t and t > 0 else "warn"
        self._print(color,   f"  {p}/{t} challenges passed on last run")
        self._print("muted",  "\n  Press  ▶ RUN TESTS  to run again.")

    # ── output helpers ────────────────────────────────────────────────────────

    def _print(self, tag: str, text: str):
        self.output_text.config(state="normal")
        self.output_text.insert("end", text + "\n", tag)
        self.output_text.see("end")
        self.output_text.config(state="disabled")

    def _clear_output(self):
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.config(state="disabled")

    def _set_brief(self, mission: str, brief: str):
        self.mission_lbl.config(text=mission)
        self.brief_lbl.config(text=brief)

    def _set_status(self, text: str, color: str = None):
        self.status_lbl.config(
            text=f"● {text}",
            fg=color or C["accent"],
        )

    def _update_progress(self, week_key: str):
        saved = self.all_results.get(week_key, {})
        p = saved.get("passed", 0)
        t = saved.get("total",  0)
        if t:
            self.progress_lbl.config(text=f"{p} / {t} challenges passed")
        else:
            self.progress_lbl.config(text="")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = LyceumRunner()
    app.mainloop()
