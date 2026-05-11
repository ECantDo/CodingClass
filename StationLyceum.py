"""
Lyceum Test Runner
------------------
Students run this file once per session. They never need to edit it.

Folder layout:
    weeks/          <- teacher drops weekN.py files here
    submissions/    <- student puts their work here (fixed filenames)
    results.json    <- auto-created, stores last run results

Week files support two modes (or both together):
    CHALLENGES      list of static test cases  (run by ▶ RUN TESTS)
    run_interactive(student_module, log)        teacher script (run by ⚡ RUN SCRIPT)

Source inspection utility (importable from week files):
    check_forbidden(student_mod, func_name, banned) -> (passed: bool, log: list[tuple])
    Checks that the named function contains none of the banned call patterns.
    Returns a (bool, [(tag, text), ...]) pair ready to use in interactive_log or log_fn.
"""

import tkinter as tk
import importlib.util
import inspect
import sys
import io
import json
import traceback
import threading
from pathlib import Path
from datetime import datetime

# ── paths ─────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.resolve()
WEEKS_DIR = BASE_DIR / "weeks"
SUBMIT_DIR = BASE_DIR / "submissions"
RESULTS_FILE = BASE_DIR / "results.json"

for _d in (WEEKS_DIR, SUBMIT_DIR):
	_d.mkdir(exist_ok=True)


# ── source inspection ─────────────────────────────────────────────────────────

def check_forbidden(student_mod, func_name: str, banned: list) -> tuple:
	"""
	Inspect the source of student_mod.func_name for forbidden function calls
	using the AST — immune to false positives from comments and string literals.

	Usage in a week file runner:
	    passed, log = check_forbidden(student_mod, "sort_manifest", ["sort", "sorted"])
	    # log is a list of (tag, text) tuples ready for interactive_log / log_fn

	Parameters:
	    student_mod   the loaded student module (as passed to run_interactive or runner())
	    func_name     name of the function to inspect (string)
	    banned        list of bare function names to forbid, e.g. ["sort", "sorted"]

	Returns:
	    (passed: bool, log: list[tuple[str, str]])
	    passed  — True if none of the banned calls were found
	    log     — list of (tag, text) pairs; tags match the station palette:
	              "pass", "fail", "muted"
	"""
	import ast

	log = []
	func = getattr(student_mod, func_name, None)
	if func is None:
		return False, [("fail", f"'{func_name}' not found in submission")]

	try:
		source = inspect.getsource(func)
	except OSError:
		return False, [("warn",
		                f"Could not read source of '{func_name}' — skipping forbidden check")]

	try:
		tree = ast.parse(inspect.cleandoc(source))
	except SyntaxError as e:
		return False, [("fail", f"Syntax error parsing {func_name}: {e}")]

	banned_set = set(banned)
	# Collect every function call name that appears in the AST.
	# ast.Call nodes have a .func that is either:
	#   ast.Name  — a plain call like sorted(...)
	#   ast.Attribute — a method call like my_list.sort(...)
	hits: dict = {}  # name -> list of line numbers
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call):
			continue
		if isinstance(node.func, ast.Name) and node.func.id in banned_set:
			hits.setdefault(node.func.id, []).append(node.lineno)
		elif isinstance(node.func, ast.Attribute) and node.func.attr in banned_set:
			hits.setdefault(node.func.attr, []).append(node.lineno)

	source_lines = source.splitlines()
	clean = True
	for name in banned:
		if name in hits:
			clean = False
			lines = hits[name]
			log.append(("fail", f"✗  Forbidden: {name}() found in {func_name}"))
			for lineno in lines:
				# lineno is relative to the start of the parsed snippet
				src_line = source_lines[lineno - 1].strip() if lineno <= len(source_lines) else ""
				log.append(("muted", f"   line {lineno}: {src_line}"))
		else:
			log.append(("pass", f"✓  {name}() not used — good"))

	return clean, log


# ── palette ───────────────────────────────────────────────────────────────────

C = {
	"bg": "#0d1117",
	"panel": "#161b22",
	"panel2": "#1c2128",
	"border": "#21262d",
	"accent": "#3fb950",
	"accent_dim": "#238636",
	"warn": "#d29922",
	"danger": "#f85149",
	"info": "#58a6ff",
	"muted": "#484f58",
	"text": "#c9d1d9",
	"text_bright": "#f0f6fc",
	"text_dim": "#6e7681",
	"story": "#79c0ff",
	"purple": "#bc8cff",
}

F = {
	"mono": ("Courier New", 11),
	"ui": ("Helvetica", 11),
	"ui_s": ("Helvetica", 10),
	"ui_b": ("Helvetica", 11, "bold"),
	"label": ("Helvetica", 8, "bold"),
	"label2": ("Helvetica", 9),
}


# ── button helper (forces colour on macOS / iOS where tk.Button ignores bg) ──

def _styled_btn(parent, text, bg, fg, active_bg, active_fg,
                font, command=None, padx=12, pady=0, cursor="hand2",
                side=None, pack_padx=0, pack_pady=0, anchor="center"):
	"""
	Returns a tk.Label styled as a button.
	tk.Button on Aqua (macOS/iOS) ignores bg/fg; Labels always respect them.
	"""
	lbl = tk.Label(parent, text=text, bg=bg, fg=fg, font=font,
	               padx=padx, pady=pady, cursor=cursor, anchor=anchor)
	if command:
		lbl.bind("<Button-1>", lambda e: command())
	lbl.bind("<Enter>", lambda e: lbl.config(bg=active_bg, fg=active_fg))
	lbl.bind("<Leave>", lambda e: lbl.config(bg=bg, fg=fg))
	return lbl


# ── week discovery ────────────────────────────────────────────────────────────

def load_week_module(path: Path):
	spec = importlib.util.spec_from_file_location(path.stem, path)
	mod = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(mod)
	return mod


def discover_weeks() -> list:
	found = []
	if not WEEKS_DIR.exists():
		return found
	for p in sorted(WEEKS_DIR.glob("week*.py")):
		if not (p.suffix == ".py" and p.stem.startswith("week")):
			continue
		try:
			mod = load_week_module(p)
			meta = getattr(mod, "WEEK_META", None)
			if not isinstance(meta, dict):
				continue
			found.append({"path": p, "module": mod, "meta": meta})
		except Exception:
			found.append({"path": p, "module": None, "meta": None,
			              "error": traceback.format_exc(limit=4)})
	return found


# ── student loader ────────────────────────────────────────────────────────────

def load_student(submit_path: Path):
	"""Returns (module, error_str). Always reloads fresh so edits are picked up."""
	if not submit_path.exists():
		return None, (
			f"File not found: submissions/{submit_path.name}\n"
			f"Name your file exactly '{submit_path.name}' and put it in the 'submissions' folder."
		)
	try:
		spec = importlib.util.spec_from_file_location("_student_work", submit_path)
		mod = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(mod)
		return mod, None
	except Exception:
		return None, f"Could not load {submit_path.name}:\n{traceback.format_exc(limit=5)}"


# ── static test logic ─────────────────────────────────────────────────────────

def run_one_test(test: dict, student_mod, submit_name: str) -> dict:
	if test.get("is_interactive_test"):
		return run_interactive_challenge(test, student_mod, submit_name)

	t = {
		"call": test.get("call", ""),
		"note": test.get("note", ""),
		"passed": False,
		"got": None,
		"expected": test.get("expected"),
		"error": None,
	}
	func = getattr(student_mod, test.get("func"), None)
	if func is None:
		t["error"] = f"function '{test.get('func')}' not found in {submit_name}"
		return t
	try:
		if test.get("is_print_test"):
			buf = io.StringIO()
			old, sys.stdout = sys.stdout, buf
			try:
				func(*test.get("args", []))
			finally:
				sys.stdout = old
			printed = buf.getvalue().strip().splitlines()
			t["got"] = printed
			t["passed"] = (printed == test["expected"])
		else:
			got = func(*test.get("args", []))
			t["got"] = got
			t["passed"] = (got == test["expected"])
	except Exception:
		t["error"] = traceback.format_exc(limit=4)
	return t


def run_static_challenges(week: dict) -> list:
	submit_path = SUBMIT_DIR / week["meta"].get("submission_file", "unknown.py")
	student_mod, err = load_student(submit_path)
	results = []
	for ch in getattr(week["module"], "CHALLENGES", []):
		r = {
			"id": ch.get("id", "?"),
			"title": ch.get("title", "Unnamed"),
			"mission": ch.get("mission", ""),
			"story_pass": ch.get("story_pass", ""),
			"load_error": err,
			"tests": [], "passed": 0, "total": 0,
		}
		if not err:
			for test in ch.get("tests", []):
				t = run_one_test(test, student_mod, submit_path.name)
				r["tests"].append(t)
				r["total"] += 1
				if t["passed"]:
					r["passed"] += 1
		results.append(r)
	return results


# ── results persistence ───────────────────────────────────────────────────────

def load_results() -> dict:
	if RESULTS_FILE.exists():
		try:
			return json.loads(RESULTS_FILE.read_text())
		except Exception:
			pass
	return {}


def save_results(data: dict):
	RESULTS_FILE.write_text(json.dumps(data, indent=2, default=str))


# ── interactive challenge runner ──────────────────────────────────────────────

def run_interactive_challenge(test: dict, student_mod, submit_name: str) -> dict:
	"""
	Runs a challenge test marked with is_interactive_test=True.
	The test must supply a 'runner' callable:
	    runner(student_func, student_mod) -> (passed: bool, log_lines: list[tuple[tag, text]])
	Both the function and the full module are passed so runners can use
	check_forbidden() or inspect other functions on the module directly.
	"""
	t = {
		"call": test.get("call", ""),
		"note": test.get("note", ""),
		"passed": False,
		"got": None,
		"expected": test.get("expected", "(interactive)"),
		"error": None,
		"interactive_log": [],  # list of (tag, text) for display
	}
	func = getattr(student_mod, test.get("func"), None)
	if func is None:
		t["error"] = f"function '{test.get('func')}' not found in {submit_name}"
		return t
	runner = test.get("runner")
	if not callable(runner):
		t["error"] = "test is missing a 'runner' callable — check the week file"
		return t
	try:
		passed, log_lines = runner(func, student_mod)
		t["passed"] = passed
		t["interactive_log"] = log_lines
	except Exception:
		t["error"] = traceback.format_exc(limit=4)
	return t


# ── GUI ───────────────────────────────────────────────────────────────────────

class LyceumRunner(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Station Lyceum — Test Runner")
		self.configure(bg=C["bg"])
		self.geometry("980x700")
		self.minsize(800, 540)

		self.weeks = []
		self.current_week = None  # int index into self.weeks
		self.all_results = load_results()
		self._tab_btns = []
		self._last_tab_key = self.all_results.get("_last_tab")  # stem of last-used week file

		# output buffer: list of (tag, text, ch_id|None)
		# ch_id links a line to a specific challenge for filtering
		self._out_buf: list = []
		self._filter_ch = None  # active challenge id filter
		self._sel_ch_row = None  # currently highlighted sidebar row

		self._build_ui()
		self._refresh_weeks()

	# ─── UI construction ──────────────────────────────────────────────────────

	def _build_ui(self):
		# top bar
		top = tk.Frame(self, bg=C["panel"], height=52)
		top.pack(fill="x")
		top.pack_propagate(False)

		tk.Label(top, text="STATION LYCEUM", bg=C["panel"], fg=C["accent"],
		         font=("Helvetica", 14, "bold"), padx=18).pack(side="left", pady=12)

		self.status_lbl = tk.Label(top, text="● ready", bg=C["panel"],
		                           fg=C["accent"], font=F["ui_s"])
		self.status_lbl.pack(side="left", pady=12)

		_styled_btn(top, "↺  Refresh weeks",
		            bg=C["panel"], fg=C["text_dim"],
		            active_bg=C["border"], active_fg=C["text"],
		            font=F["ui_s"], command=self._refresh_weeks,
		            padx=12, pady=5
		            ).pack(side="right", pady=10, padx=12)

		tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

		# week tab row — horizontally scrollable so tabs never squish
		tab_outer = tk.Frame(self, bg=C["panel"])
		tab_outer.pack(fill="x")

		self._tab_canvas = tk.Canvas(tab_outer, bg=C["panel"],
		                             height=42, highlightthickness=0)
		self._tab_canvas.pack(fill="x", expand=True, side="top")

		tab_hscroll = tk.Scrollbar(tab_outer, orient="horizontal",
		                           command=self._tab_canvas.xview,
		                           bg=C["panel"], troughcolor=C["panel"],
		                           highlightthickness=0)
		# only show scrollbar when it's actually needed (packed in _refresh_weeks)
		self._tab_hscroll = tab_hscroll
		self._tab_canvas.configure(xscrollcommand=tab_hscroll.set)

		self.tab_row = tk.Frame(self._tab_canvas, bg=C["panel"])
		self._tab_win = self._tab_canvas.create_window(
			(0, 0), window=self.tab_row, anchor="nw")

		def _on_tab_frame_configure(e):
			self._tab_canvas.configure(
				scrollregion=self._tab_canvas.bbox("all"))
			# show scrollbar only when content wider than canvas
			if self.tab_row.winfo_reqwidth() > self._tab_canvas.winfo_width():
				self._tab_hscroll.pack(fill="x", side="top")
			else:
				self._tab_hscroll.pack_forget()

		self.tab_row.bind("<Configure>", _on_tab_frame_configure)
		# allow mouse-wheel / trackpad horizontal scroll on the tab row
		self._tab_canvas.bind("<MouseWheel>",
		                      lambda e: self._tab_canvas.xview_scroll(-1 * (e.delta // 120), "units"))
		self._tab_canvas.bind("<Shift-MouseWheel>",
		                      lambda e: self._tab_canvas.xview_scroll(-1 * (e.delta // 120), "units"))
		tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

		# body
		body = tk.Frame(self, bg=C["bg"])
		body.pack(fill="both", expand=True)

		# ── left sidebar ──
		self.left_panel = tk.Frame(body, bg=C["panel"], width=224)
		self.left_panel.pack(fill="y", side="left")
		self.left_panel.pack_propagate(False)
		tk.Frame(body, bg=C["border"], width=1).pack(fill="y", side="left")

		# ── right column ──
		right = tk.Frame(body, bg=C["bg"])
		right.pack(fill="both", expand=True)

		# mission brief
		brief_bar = tk.Frame(right, bg=C["panel"], height=82)
		brief_bar.pack(fill="x")
		brief_bar.pack_propagate(False)
		bi = tk.Frame(brief_bar, bg=C["panel"])
		bi.pack(fill="both", expand=True, padx=16, pady=10)

		self.mission_lbl = tk.Label(bi, text="SELECT A WEEK TO BEGIN",
		                            bg=C["panel"], fg=C["warn"],
		                            font=("Helvetica", 9, "bold"), anchor="w")
		self.mission_lbl.pack(fill="x")
		self.brief_lbl = tk.Label(bi,
		                          text="No week loaded. Drop a week file into 'weeks/' and click Refresh.",
		                          bg=C["panel"], fg=C["text_dim"], font=F["ui_s"],
		                          anchor="w", wraplength=680, justify="left")
		self.brief_lbl.pack(fill="x", pady=(3, 0))

		tk.Frame(right, bg=C["border"], height=1).pack(fill="x")

		# output header row
		out_hdr = tk.Frame(right, bg=C["panel"])
		out_hdr.pack(fill="x")

		tk.Label(out_hdr, text="STATION OUTPUT", bg=C["panel"], fg=C["text_dim"],
		         font=F["label"], padx=16, pady=5, anchor="w").pack(side="left")

		# filter pill (hidden until a challenge is clicked)
		self._filter_frame = tk.Frame(out_hdr, bg=C["panel"])
		self._filter_frame.pack(side="left")
		self._filter_lbl = tk.Label(self._filter_frame, text="",
		                            bg=C["panel"], fg=C["info"], font=F["ui_s"])
		self._filter_lbl.pack(side="left")
		self._clear_filter_btn = _styled_btn(
			self._filter_frame, "✕ show all",
			bg=C["panel"], fg=C["text_dim"],
			active_bg=C["border"], active_fg=C["text"],
			font=("Helvetica", 9), command=self._clear_filter, padx=6)
		# shown on demand via pack()

		self.timestamp_lbl = tk.Label(out_hdr, text="", bg=C["panel"],
		                              fg=C["muted"], font=("Helvetica", 8), padx=16)
		self.timestamp_lbl.pack(side="right")
		tk.Frame(right, bg=C["border"], height=1).pack(fill="x")

		# ── run bar (bottom) ──
		# Pack BEFORE out_wrap so tkinter reserves its height first.
		# If out_wrap is packed first with expand=True, it grabs all remaining
		# space and the run bar gets pushed off-screen at small window sizes.
		tk.Frame(right, bg=C["border"], height=1).pack(fill="x", side="bottom")

		run_bar = tk.Frame(right, bg=C["panel"], height=52)
		run_bar.pack(fill="x", side="bottom")
		run_bar.pack_propagate(False)

		# output text (packed after run bar so it only fills what's left)
		out_wrap = tk.Frame(right, bg=C["bg"])
		out_wrap.pack(fill="both", expand=True)

		self.output_text = tk.Text(
			out_wrap, bg=C["bg"], fg=C["text"],
			font=F["mono"], relief="flat",
			padx=16, pady=12, wrap="word",
			state="disabled", cursor="arrow")
		self.output_text.pack(fill="both", expand=True, side="left")

		sb = tk.Scrollbar(out_wrap, command=self.output_text.yview, bg=C["panel"])
		sb.pack(fill="y", side="right")
		self.output_text.config(yscrollcommand=sb.set)

		for tag, fg, extra in [
			("system", C["text_dim"], {}),
			("pass", C["accent"], {}),
			("fail", C["danger"], {}),
			("warn", C["warn"], {}),
			("info", C["info"], {}),
			("story", C["story"], {}),
			("error", C["danger"], {}),
			("bright", C["text_bright"], {}),
			("muted", C["text_dim"], {}),
			("heading", C["accent"], {"font": ("Helvetica", 10, "bold")}),
			("interactive", C["purple"], {}),
		]:
			self.output_text.tag_config(tag, foreground=fg, **extra)

		self.run_btn = _styled_btn(
			run_bar, "▶   RUN TESTS",
			bg=C["accent_dim"], fg=C["text_bright"],
			active_bg=C["accent"], active_fg=C["bg"],
			font=("Helvetica", 12, "bold"), padx=28, pady=10,
			command=self._run_static)
		self.run_btn.pack(side="left", padx=16, pady=10)

		# interactive button — shown only when week defines run_interactive()
		self.interactive_btn = _styled_btn(
			run_bar, "⚡  RUN SCRIPT",
			bg=C["panel"], fg=C["purple"],
			active_bg=C["panel2"], active_fg=C["purple"],
			font=("Helvetica", 12, "bold"), padx=28, pady=10,
			command=self._run_interactive)
		# packed on demand

		self.progress_lbl = tk.Label(run_bar, text="", bg=C["panel"],
		                             fg=C["text_dim"], font=F["ui_s"])
		self.progress_lbl.pack(side="left", pady=10)

		_styled_btn(run_bar, "Clear output",
		            bg=C["panel"], fg=C["text_dim"],
		            active_bg=C["border"], active_fg=C["text"],
		            font=F["ui_s"], command=self._user_clear, padx=12, pady=10
		            ).pack(side="right", padx=16, pady=10)

	# ─── week tabs ────────────────────────────────────────────────────────────

	def _refresh_weeks(self):
		for w in self.tab_row.winfo_children():
			w.destroy()
		self._tab_btns = []
		self.weeks = discover_weeks()

		if not self.weeks:
			tk.Label(self.tab_row,
			         text="  No week files found in weeks/ folder",
			         bg=C["panel"], fg=C["text_dim"],
			         font=F["ui_s"], padx=12, pady=10).pack(side="left")
			self._set_status("no weeks loaded", C["warn"])
			return

		for i, week in enumerate(self.weeks):
			meta = (week.get("meta") or {})
			label = meta.get("tab_label", week["path"].stem)
			color = C["danger"] if week.get("error") else C["text_dim"]
			btn = _styled_btn(
				self.tab_row, label,
				bg=C["panel"], fg=color,
				active_bg=C["panel2"], active_fg=C["text"],
				font=F["ui"], padx=16, pady=10,
				command=lambda idx=i: self._select_week(idx))
			btn.pack(side="left")
			self._tab_btns.append(btn)

		# restore last-used tab, fall back to 0
		start_idx = 0
		if self._last_tab_key:
			for i, w in enumerate(self.weeks):
				if w["path"].stem == self._last_tab_key:
					start_idx = i
					break
		self._select_week(start_idx)
		self._set_status(f"{len(self.weeks)} week(s) loaded", C["accent"])

	def _select_week(self, idx: int):
		self.current_week = idx
		self._out_buf = []
		self._clear_filter(render=False)

		for i, btn in enumerate(self._tab_btns):
			if i == idx:
				btn.config(bg=C["panel2"], fg=C["text_bright"],
				           font=("Helvetica", 11, "bold"))
			else:
				btn.config(bg=C["panel"], fg=C["text_dim"], font=F["ui"])

		week = self.weeks[idx]

		# persist last-used tab
		self._last_tab_key = week["path"].stem
		self.all_results["_last_tab"] = self._last_tab_key
		save_results(self.all_results)

		if week.get("error"):
			self.mission_lbl.config(text="LOAD ERROR")
			self.brief_lbl.config(text=week["error"])
			self._rebuild_sidebar([])
			self._show_interactive_btn(False)
			return

		meta = week["meta"]
		self.mission_lbl.config(text=meta.get("tab_label", "").upper())
		self.brief_lbl.config(text=meta.get("description", ""))

		has_interactive = callable(getattr(week["module"], "run_interactive", None))
		self._rebuild_sidebar(getattr(week["module"], "CHALLENGES", []))
		self._show_interactive_btn(has_interactive)

		week_key = week["path"].stem
		if week_key in self.all_results:
			self._show_saved_summary(week_key)
		else:
			self._out_buf = []
			self._buf("system", f"[ {meta.get('title', week['path'].stem)} ]")
			self._buf("system", "  Press  ▶ RUN TESTS  to test your code.")
			if has_interactive:
				self._buf("interactive",
				          "  Press  ⚡ RUN SCRIPT  to run the interactive test script.")
			self._buf("muted",
			          f"  Expected file: submissions/{meta.get('submission_file', '?')}")
			self._flush()

		self._update_progress(week_key)

	def _show_interactive_btn(self, show: bool):
		if show:
			self.interactive_btn.pack(side="left", padx=(0, 8), pady=10)
		else:
			self.interactive_btn.pack_forget()

	# ─── sidebar ──────────────────────────────────────────────────────────────

	def _rebuild_sidebar(self, challenges: list):
		for w in self.left_panel.winfo_children():
			w.destroy()
		self._sel_ch_row = None

		tk.Label(self.left_panel, text="CHALLENGES",
		         bg=C["panel"], fg=C["text_dim"],
		         font=F["label"], anchor="w", padx=14, pady=8).pack(fill="x")
		tk.Label(self.left_panel,
		         text="click to filter output",
		         bg=C["panel"], fg=C["muted"],
		         font=("Helvetica", 8), anchor="w", padx=14).pack(fill="x")
		tk.Frame(self.left_panel, bg=C["border"], height=1).pack(fill="x")

		if not challenges:
			tk.Label(self.left_panel, text="No static challenges",
			         bg=C["panel"], fg=C["muted"],
			         font=F["ui_s"], padx=14, pady=10).pack(fill="x")
			return

		week_key = self.weeks[self.current_week]["path"].stem \
			if self.current_week is not None else None
		saved = self.all_results.get(week_key, {}).get("challenges", {}) \
			if week_key else {}

		for ch in challenges:
			ch_id = ch.get("id", ch.get("title", "?"))
			ch_sv = saved.get(ch_id, {})
			passed = ch_sv.get("passed", 0)
			total = ch_sv.get("total", 0)

			if total == 0:
				bar_col = C["muted"]
				status_txt = "not run"
			elif passed == total:
				bar_col = C["accent"]
				status_txt = f"✓  {passed}/{total}"
			else:
				bar_col = C["danger"]
				status_txt = f"✗  {passed}/{total}"

			row = tk.Frame(self.left_panel, bg=C["panel"], cursor="hand2")
			row.pack(fill="x")

			accent_bar = tk.Frame(row, bg=bar_col, width=3)
			accent_bar.pack(fill="y", side="left")

			inner = tk.Frame(row, bg=C["panel"])
			inner.pack(fill="x", padx=10, pady=7)

			t_lbl = tk.Label(inner, text=ch.get("title", "Unnamed"),
			                 bg=C["panel"], fg=C["text"],
			                 font=F["ui_s"], anchor="w")
			t_lbl.pack(fill="x")

			s_lbl = tk.Label(inner, text=status_txt,
			                 bg=C["panel"], fg=bar_col,
			                 font=("Helvetica", 9), anchor="w")
			s_lbl.pack(fill="x")

			tk.Frame(self.left_panel, bg=C["border"], height=1).pack(fill="x")

			# bind click + hover on every widget in the row
			def _bind(w, cid=ch_id, r=row):
				w.bind("<Button-1>", lambda e: self._click_challenge(cid, r))
				w.bind("<Enter>", lambda e, _r=r: self._row_hover(_r, True))
				w.bind("<Leave>", lambda e, _r=r, _cid=cid: self._row_hover(_r, False, _cid))

			for widget in (row, accent_bar, inner, t_lbl, s_lbl):
				_bind(widget)

	def _row_hover(self, row: tk.Widget, entering: bool, ch_id: str = None):
		# don't un-highlight the actively selected row on leave
		if not entering and self._filter_ch == ch_id:
			return
		bg = C["panel2"] if entering else C["panel"]
		row.config(bg=bg)
		for w in row.winfo_children():
			if isinstance(w, (tk.Frame, tk.Label)):
				w.config(bg=bg)

	def _click_challenge(self, ch_id: str, row: tk.Widget):
		if self._filter_ch == ch_id:
			self._clear_filter()
			return

		# deselect previous
		if self._sel_ch_row:
			self._row_hover(self._sel_ch_row, False, self._filter_ch)

		self._filter_ch = ch_id
		self._sel_ch_row = row
		self._row_hover(row, True)

		# find human title
		title = ch_id
		if self.current_week is not None:
			for ch in getattr(self.weeks[self.current_week]["module"],
			                  "CHALLENGES", []):
				if ch.get("id") == ch_id:
					title = ch.get("title", ch_id)
					break

		self._filter_lbl.config(text=f"  showing: {title}  ")
		self._clear_filter_btn.pack(side="left")
		self._render_filtered()

	def _clear_filter(self, render: bool = True):
		if self._sel_ch_row:
			self._row_hover(self._sel_ch_row, False, self._filter_ch)
			self._sel_ch_row = None
		self._filter_ch = None
		self._filter_lbl.config(text="")
		self._clear_filter_btn.pack_forget()
		if render:
			self._render_filtered()

	def _render_filtered(self):
		"""Redraw output from buffer, applying the active challenge filter."""
		self._wipe_output()
		active = self._filter_ch
		for (tag, text, ch_id) in self._out_buf:
			# show if: no filter, or line is untagged (headers/summaries), or matches
			if active is None or ch_id is None or ch_id == active:
				self._write(tag, text)

	# ─── static test run ──────────────────────────────────────────────────────

	def _run_static(self):
		if self.current_week is None:
			return
		week = self.weeks[self.current_week]
		if week.get("error"):
			return

		# remember which challenge was filtered so we can restore it after
		_preserved_filter = self._filter_ch
		_preserved_row = self._sel_ch_row

		self._lock_buttons("  Running…")
		self._set_status("running tests…", C["warn"])
		self._out_buf = []
		self._clear_filter(render=False)
		self._wipe_output()

		def worker():
			results = run_static_challenges(week)
			self.after(0, lambda: self._show_static_results(
				week, results, _preserved_filter, _preserved_row))

		threading.Thread(target=worker, daemon=True).start()

	def _show_static_results(self, week: dict, results: list,
	                         restore_filter=None, restore_row=None):
		meta = week["meta"]
		week_key = week["path"].stem
		now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		self.timestamp_lbl.config(text=f"last run: {now}")

		total_ch = len(results)
		passed_ch = 0
		ch_saved = {}

		self._buf("heading", f"\n  {meta.get('title', week_key).upper()}")
		self._buf("system", f"  {now}\n")

		for ch in results:
			ch_id = ch["id"]
			load_err = ch.get("load_error")

			self._buf("bright", f"  ── {ch['mission'] or ch['title']} ──",
			          cid=ch_id)

			if load_err:
				self._buf("fail", f"  ✗  {ch['title']}", cid=ch_id)
				for ln in load_err.splitlines():
					self._buf("error", f"  {ln}", cid=ch_id)
				self._buf("system", "", cid=ch_id)
				ch_saved[ch_id] = {"passed": 0, "total": 0}
				continue

			all_pass = ch["passed"] == ch["total"] > 0

			for t in ch["tests"]:
				if t["error"]:
					self._buf("fail", f"  ✗  {t['call']}", cid=ch_id)
					for ln in t["error"].strip().splitlines()[-5:]:
						self._buf("error", f"     {ln}", cid=ch_id)
				elif t.get("interactive_log"):
					# render each line emitted by the interactive runner
					for (tag, text) in t["interactive_log"]:
						self._buf(tag, f"  {text}", cid=ch_id)
				elif t["passed"]:
					note = f"  ({t['note']})" if t["note"] else ""
					self._buf("pass",
					          f"  ✓  {t['call']} → {repr(t['got'])}{note}",
					          cid=ch_id)
				else:
					self._buf("fail", f"  ✗  {t['call']}", cid=ch_id)
					self._buf("muted", f"     expected: {repr(t['expected'])}",
					          cid=ch_id)
					self._buf("muted", f"     got:      {repr(t['got'])}",
					          cid=ch_id)

			icon = "✓" if all_pass else "✗"
			self._buf("pass" if all_pass else "fail",
			          f"  {icon}  {ch['title']}  —  {ch['passed']}/{ch['total']} passed",
			          cid=ch_id)

			if all_pass:
				if ch.get("story_pass"):
					self._buf("story", f"\n  {ch['story_pass']}", cid=ch_id)
				passed_ch += 1

			self._buf("system", "", cid=ch_id)
			ch_saved[ch_id] = {"passed": ch["passed"], "total": ch["total"]}

		self._buf("system", "  " + "─" * 48)
		if passed_ch == total_ch > 0:
			self._buf("pass", f"\n  ALL CHALLENGES PASSED  ({passed_ch}/{total_ch})\n")
		else:
			self._buf("warn", f"\n  {passed_ch}/{total_ch} challenges fully passed\n")

		# restore challenge filter if one was active before the run
		if restore_filter:
			self._filter_ch = restore_filter
			self._sel_ch_row = restore_row
			title = restore_filter
			if self.current_week is not None:
				for ch in getattr(self.weeks[self.current_week]["module"],
				                  "CHALLENGES", []):
					if ch.get("id") == restore_filter:
						title = ch.get("title", restore_filter)
						break
			self._filter_lbl.config(text=f"  showing: {title}  ")
			self._clear_filter_btn.pack(side="left")
			if restore_row:
				self._row_hover(restore_row, True)

		self._render_filtered()

		self.all_results[week_key] = {
			"timestamp": now,
			"passed": passed_ch,
			"total": total_ch,
			"challenges": ch_saved,
		}
		save_results(self.all_results)
		self._rebuild_sidebar(getattr(week["module"], "CHALLENGES", []))
		self._update_progress(week_key)
		self._unlock_buttons()
		self._set_status(
			f"{passed_ch}/{total_ch} challenges passed",
			C["accent"] if passed_ch == total_ch else C["warn"])

	# ─── interactive script run ───────────────────────────────────────────────

	def _run_interactive(self):
		if self.current_week is None:
			return
		week = self.weeks[self.current_week]
		if week.get("error"):
			return

		self._lock_buttons("⚡  Running…", interactive=True)
		self._set_status("running interactive script…", C["purple"])
		self._out_buf = []
		self._clear_filter(render=False)
		self._wipe_output()

		now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		self._buf("interactive",
		          f"\n  ⚡  INTERACTIVE SCRIPT — {week['meta'].get('title', '')}")
		self._buf("system", f"  {now}\n")
		self._flush()

		submit_path = SUBMIT_DIR / week["meta"].get("submission_file", "unknown.py")
		student_mod, err = load_student(submit_path)

		if err:
			for ln in err.splitlines():
				self._buf("error", f"  {ln}")
			self._buf("system", "\n  [ script aborted — fix the error above first ]\n")
			self._flush()
			self._unlock_buttons()
			self._set_status("load error", C["danger"])
			return

		run_fn = getattr(week["module"], "run_interactive", None)
		if not callable(run_fn):
			self._buf("error", "  run_interactive() not defined in this week file.")
			self._flush()
			self._unlock_buttons()
			return

		def log_fn(tag: str, text: str):
			"""Called from worker thread — schedules GUI update on main thread."""
			self.after(0, lambda t=tag, m=text: self._stream_line(t, m))

		def done_fn():
			self.after(0, self._interactive_done)

		def worker():
			try:
				run_fn(student_mod, log_fn)
			except Exception:
				msg = traceback.format_exc(limit=6)
				self.after(0, lambda: self._stream_line("error", msg))
			done_fn()

		threading.Thread(target=worker, daemon=True).start()

	def _stream_line(self, tag: str, text: str):
		for line in (str(text).splitlines() or [""]):
			entry = (tag, f"  {line}", None)
			self._out_buf.append(entry)
			self._write(tag, f"  {line}")

	def _interactive_done(self):
		self._buf("system", "\n  [ script finished ]\n")
		self._write("system", "\n  [ script finished ]\n")
		self._unlock_buttons()
		self._set_status("script finished", C["purple"])

	# ─── output helpers ───────────────────────────────────────────────────────

	def _buf(self, tag: str, text: str, cid=None):
		self._out_buf.append((tag, text, cid))

	def _write(self, tag: str, text: str):
		self.output_text.config(state="normal")
		self.output_text.insert("end", text + "\n", tag)
		self.output_text.see("end")
		self.output_text.config(state="disabled")

	def _wipe_output(self):
		self.output_text.config(state="normal")
		self.output_text.delete("1.0", "end")
		self.output_text.config(state="disabled")

	def _flush(self):
		"""Write all buffered lines to widget (no filter)."""
		self._wipe_output()
		for (tag, text, _) in self._out_buf:
			self._write(tag, text)

	def _user_clear(self):
		self._out_buf = []
		self._clear_filter(render=False)
		self._wipe_output()

	# ─── misc ─────────────────────────────────────────────────────────────────

	def _lock_buttons(self, label: str, interactive: bool = False):
		if interactive:
			self.interactive_btn.config(text=label, fg=C["muted"], cursor="")
			self.interactive_btn.unbind("<Button-1>")
			self.run_btn.config(fg=C["muted"], cursor="")
			self.run_btn.unbind("<Button-1>")
		else:
			self.run_btn.config(text=label, fg=C["muted"], cursor="")
			self.run_btn.unbind("<Button-1>")
			self.interactive_btn.config(fg=C["muted"], cursor="")
			self.interactive_btn.unbind("<Button-1>")

	def _unlock_buttons(self):
		self.run_btn.config(text="▶   RUN TESTS",
		                    fg=C["text_bright"], cursor="hand2")
		self.run_btn.bind("<Button-1>", lambda e: self._run_static())
		self.interactive_btn.config(text="⚡  RUN SCRIPT",
		                            fg=C["purple"], cursor="hand2")
		self.interactive_btn.bind("<Button-1>", lambda e: self._run_interactive())

	def _set_status(self, text: str, color: str = None):
		self.status_lbl.config(text=f"● {text}", fg=color or C["accent"])

	def _show_saved_summary(self, week_key: str):
		saved = self.all_results.get(week_key, {})
		ts = saved.get("timestamp", "unknown")
		p = saved.get("passed", 0)
		t = saved.get("total", 0)
		self._out_buf = []
		self._buf("system", f"  Last run: {ts}")
		self._buf("system", "  Results loaded from results.json\n")
		self._buf("pass" if (p == t > 0) else "warn",
		          f"  {p}/{t} challenges passed on last run")
		self._buf("muted", "\n  Press  ▶ RUN TESTS  to run again.")
		self._flush()

	def _update_progress(self, week_key: str):
		saved = self.all_results.get(week_key, {})
		p = saved.get("passed", 0)
		t = saved.get("total", 0)
		self.progress_lbl.config(
			text=f"{p} / {t} challenges passed" if t else "")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
	app = LyceumRunner()
	app.mainloop()