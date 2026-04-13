# Station Lyceum — Test Runner

A standalone Python test runner for the Lyceum coding course.
Students code in their own IDE. This tool just runs the tests and shows results.

---

## Folder layout

```
lyceum/
├── StationLyceum.py            ← run this to launch the GUI
├── weeks/                      ← teacher drops week*.py files here before class
│   ├── week0.py                ← example testing to confirm everything is working
│   ├── week1.py
│   └── week2.py
├── submissions/                ← student puts their work here
│   ├── week0_work.py           ← example program
│   ├── week1_work.py
│   └── week2_work.py
├── results.json                ← auto-created, stores last run results
└── README.md
```

---

## For students

1. Open your week's starter file from `submissions/` in VSCode or PyCharm.
2. Write your functions. Save the file.
3. Run `runner.py` (or just leave it open — it remembers your last results).
4. Click the correct week tab, then press **▶ RUN TESTS**.
5. Read the output. Fix any failing tests. Run again.

Your results are saved automatically. Next time you open the runner,
it will show you where you left off.

---

## For teachers

### Adding a new week

1. Create a new `weekN.py` file in the `weeks/` folder.
2. Copy the structure from `week1.py` or `week2.py`.
3. Fill in `WEEK_META` and the `CHALLENGES` list.
4. Post the file online or distribute it — students drop it in their `weeks/` folder.

### What a week file needs

Every week file must define two things at the top level:

```python
WEEK_META = {
    "tab_label":       "Week 3 — Systems Scan",   # shown on the tab
    "title":           "Week 3: Systems Scan",     # shown in output
    "description":     "What the student needs to do...",
    "submission_file": "week3_work.py",            # file in submissions/
}

CHALLENGES = [
    {
        "id":         "w3c1",           # unique string, used in results.json
        "title":      "Fix the loop",   # shown in sidebar
        "mission":    "DIAGNOSTIC — STEP 1",
        "story_pass": "[ Flavour text shown when all tests pass ]",
        "tests": [
            {
                "call":     "scan(systems)",        # human-readable, shown in output
                "func":     "scan",                 # actual function name in student's file
                "args":     [["engine", "life_support"]],
                "expected": ["engine: OK", "life_support: OK"],
            },
        ],
    },
]
```

### Test case options

| Key            | Required | Description |
|----------------|----------|-------------|
| `call`         | yes      | Label shown in the output |
| `func`         | yes      | Name of the function in the student's file |
| `args`         | yes      | List of arguments (can be empty list `[]`) |
| `expected`     | yes      | Exact return value to compare against |
| `note`         | no       | Extra note shown next to the result |
| `is_print_test`| no       | If `True`, captures printed output instead of return value. `expected` should then be a list of strings, one per printed line. |

---

## Requirements

- Python 3.9 or newer
- No external packages needed — uses only the standard library (`tkinter`, `importlib`, `json`, `threading`)

### Running

```bash
python StationLyceum.py
```

Or double-click `runner.py` if your system has Python associated with `.py` files.
