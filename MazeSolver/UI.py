"""
grid_ui.py — Reusable tkinter grid UI base
Designed to work for Game of Life, maze games, or any cell-based app.

Usage:
    Subclass GridApp and override:
        - on_cell_click(row, col, button)   # left=1, right=3
        - on_step()                          # called each tick when running
        - setup()                            # called once after __init__

    Then call .run() to start the mainloop.
"""

import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Color configuration — change anything here or swap at runtime
# ---------------------------------------------------------------------------

@dataclass
class ColorConfig:
	# UI Colors
	background: str = "#000000"  # window / canvas background
	grid_line: str = "#3f3f46"  # lines between cells
	ui_bg: str = "#09090b"  # sidebar / toolbar background
	ui_fg: str = "#e0e0e0"  # label text
	button_bg: str = "#3c0366"  # button face
	button_fg: str = "#e0e0e0"  # button text
	button_active: str = "#e94560"  # button hover/active

	# Cell Colors
	cell_default: str = "#18181b"
	cell_white: str = "#d4d4d8"



# ---------------------------------------------------------------------------
# The base grid application
# ---------------------------------------------------------------------------

class GridApp:
	def __init__(
			self,
			rows: int = 30,
			cols: int = 30,
			cell_size: int = round((1080 - 90) / 30),
			title: str = "Grid App",
			tick_ms: int = 100,
			colors: Optional[ColorConfig] = None,
	):
		self.rows = rows
		self.cols = cols
		self.cell_size = cell_size
		self.tick_ms = tick_ms
		self.colors = colors or ColorConfig()

		# Grid state: 2-D list of color strings (None = default dead/empty)
		self.grid: list[list[Optional[str]]] = [
			[ColorConfig.cell_default] * cols for _ in range(rows)
		]

		self._running = False
		self._after_id = None

		# Build UI
		self.root = tk.Tk()
		self.root.title(title)
		self.root.configure(bg=self.colors.ui_bg)
		self._build_ui()
		self.setup()  # subclass hook

	# ------------------------------------------------------------------
	# Subclass hooks — override these
	# ------------------------------------------------------------------

	def setup(self):
		"""Called once after the UI is ready. Put init logic here."""
		pass

	def on_cell_click(self, row: int, col: int, button: int):
		"""
		Called when the user clicks a cell.
		button: 1 = left, 2 = middle, 3 = right
		Default: left-click toggles alive/dead.
		"""
		pass

	def on_step(self):
		"""Called each tick while running. Put your simulation logic here."""
		pass

	# ------------------------------------------------------------------
	# Grid helpers
	# ------------------------------------------------------------------

	def get_cell(self, row: int, col: int) -> Optional[str]:
		"""Returns the color string for a cell, or None if empty/dead."""
		return self.grid[row][col]

	def set_cell(self, row: int, col: int, color: Optional[str]):
		"""Set a cell's color and redraw it. Pass None to clear."""
		self.grid[row][col] = color
		self._draw_cell(row, col)

	def set_all(self, color: Optional[str]):
		"""Fill every cell with a color (or None to clear)."""
		for r in range(self.rows):
			for c in range(self.cols):
				self.grid[r][c] = color
		self._draw_all()

	def clear(self):
		"""Reset the whole grid to empty."""
		self.set_all(None)

	# ------------------------------------------------------------------
	# Simulation control
	# ------------------------------------------------------------------

	def start(self):
		if not self._running:
			self._running = True
			self._tick()

	def stop(self):
		self._running = False
		if self._after_id:
			self.root.after_cancel(self._after_id)
			self._after_id = None

	def step(self):
		"""Advance exactly one tick (useful for manual stepping)."""
		self.on_step()

	def toggle(self):
		if self._running:
			self.stop()
		else:
			self.start()

	def _tick(self):
		if self._running:
			self.on_step()
			self._after_id = self.root.after(self.tick_ms, self._tick)

	# ------------------------------------------------------------------
	# Toolbar helpers — call from setup() to add buttons/sliders
	# ------------------------------------------------------------------

	def add_button(self, label: str, command, row: int = None, col: int = None):
		"""Add a button to the sidebar. Returns the Button widget."""
		btn = tk.Button(
			self._sidebar,
			text=label,
			command=command,
			bg=self.colors.button_bg,
			fg=self.colors.button_fg,
			activebackground=self.colors.button_active,
			activeforeground=self.colors.button_fg,
			relief="flat",
			padx=8, pady=4,
			cursor="hand2",
		)
		btn.pack(fill="x", padx=8, pady=3)
		return btn

	def add_label(self, text: str):
		"""Add a text label to the sidebar."""
		lbl = tk.Label(
			self._sidebar,
			text=text,
			bg=self.colors.ui_bg,
			fg=self.colors.ui_fg,
			anchor="w",
		)
		lbl.pack(fill="x", padx=8, pady=(8, 0))
		return lbl

	def add_slider(self, label: str, from_: float, to: float,
	               default: float = None, command=None):
		"""Add a labeled Scale slider to the sidebar. Returns the Scale widget."""
		self.add_label(label)
		var = tk.DoubleVar(value=default if default is not None else from_)
		slider = tk.Scale(
			self._sidebar,
			variable=var,
			from_=from_, to=to,
			orient="horizontal",
			bg=self.colors.ui_bg,
			fg=self.colors.ui_fg,
			troughcolor=self.colors.button_bg,
			highlightthickness=0,
			command=command,
		)
		slider.pack(fill="x", padx=8, pady=2)
		return slider, var

	def add_separator(self):
		sep = tk.Frame(self._sidebar, height=2, bg=self.colors.grid_line)
		sep.pack(fill="x", padx=8, pady=6)

	# ------------------------------------------------------------------
	# Internal: UI construction
	# ------------------------------------------------------------------

	def _build_ui(self):
		c = self.colors
		canvas_w = self.cols * self.cell_size
		canvas_h = self.rows * self.cell_size

		# Main frame
		main = tk.Frame(self.root, bg=c.ui_bg)
		main.pack(fill="both", expand=True)

		# Canvas
		self._canvas = tk.Canvas(
			main,
			width=canvas_w,
			height=canvas_h,
			bg=c.background,
			highlightthickness=0,
		)
		self._canvas.grid(row=0, column=0, padx=(8, 0), pady=8)

		# Sidebar
		self._sidebar = tk.Frame(main, bg=c.ui_bg, width=160)
		self._sidebar.grid(row=0, column=1, sticky="ns", padx=8, pady=8)
		self._sidebar.grid_propagate(False)

		# Default controls
		self.add_label("Controls")
		self.add_button("▶ / ⏸  Toggle", self.toggle)
		self.add_button("⏭  Step", self.step)
		self.add_button("🗑  Clear", self.clear)
		self.add_separator()

		# Draw grid lines and initial cells
		self._cell_ids: list[list[int]] = []
		for r in range(self.rows):
			row_ids = []
			for col in range(self.cols):
				x0 = col * self.cell_size
				y0 = r * self.cell_size
				x1 = x0 + self.cell_size
				y1 = y0 + self.cell_size
				rect_id = self._canvas.create_rectangle(
					x0, y0, x1, y1,
					fill=c.cell_default,
					outline=c.grid_line,
					width=2,
				)
				row_ids.append(rect_id)
			self._cell_ids.append(row_ids)

		# Mouse bindings
		self._canvas.bind("<Button-1>", lambda e: self._on_mouse(e, 1))
		self._canvas.bind("<B1-Motion>", lambda e: self._on_mouse(e, 1))
		self._canvas.bind("<Button-3>", lambda e: self._on_mouse(e, 3))
		self._canvas.bind("<B3-Motion>", lambda e: self._on_mouse(e, 3))
		self._canvas.bind("<Button-2>", lambda e: self._on_mouse(e, 2))

		# Keyboard shortcut: spacebar = toggle
		self.root.bind("<space>", lambda e: self.toggle())
		self.root.bind("<Return>", lambda e: self.step())

	def _on_mouse(self, event, button: int):
		col = event.x // self.cell_size
		row = event.y // self.cell_size
		if 0 <= row < self.rows and 0 <= col < self.cols:
			self.on_cell_click(row, col, button)

	def _draw_cell(self, row: int, col: int):
		color = self.grid[row][col]
		fill = color if color is not None else self.colors.cell_default
		self._canvas.itemconfig(self._cell_ids[row][col], fill=fill)

	def _draw_all(self):
		for r in range(self.rows):
			for c in range(self.cols):
				self._draw_cell(r, c)

	# ------------------------------------------------------------------
	# Run
	# ------------------------------------------------------------------

	def run(self):
		self.root.mainloop()


# ---------------------------------------------------------------------------
# Example: minimal Game of Life — delete or replace with your own subclass
# ---------------------------------------------------------------------------

if __name__ == "__main__":
	app = GridApp()
	app.run()
	pass