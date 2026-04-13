"""
week1.py — Hello, Recruit
--------------------------
Teacher distributes this file. Students drop it into their weeks/ folder.
The runner picks it up automatically on launch (or after clicking Refresh).

Students write their code in:  submissions/week1_work.py
"""

WEEK_META = {
	"tab_label": "Week 0 — Startup Testing",
	"title": "Week 0: Startup Testing",
	"description": (
		"The station is just coming online, make sure you have installed everything correctly. "
		"Press Run Tests to confirm everything is setup properly."
	),
	"submission_file": "week0_work.py",
}

# ─────────────────────────────────────────────────────────────────────────────
# Each challenge has:
#   id          – unique string key (used in results.json)
#   title       – shown in sidebar
#   mission     – short heading shown in output
#   story_pass  – flavour text printed when ALL tests in this challenge pass
#   tests       – list of individual test cases
#
# Each test case has:
#   call        – human-readable description shown in output  e.g. greet_recruit("Alex")
#   func        – name of the function to call in the student's file
#   args        – list of positional arguments to pass
#   expected    – the exact value (or list of lines) the function must return
#   note        – optional extra note shown next to the result  (optional)
#   is_print_test – if True, captures stdout instead of return value  (optional)
# ─────────────────────────────────────────────────────────────────────────────

CHALLENGES = [
	{
		"id": "w0c1",
		"title": "Hello world",
		"mission": "BOOT SEQUENCE — STEP 1",
		"story_pass": (
			"[ You have said hello to the world! ]"
		),
		"tests": [
			{
				"call": 'hello_world()',
				"func": "hello_world",
				"args": [],
				"expected": "Hello, World!",
			},
			{
				"call": 'hello_world()',
				"func": "hello_world",
				"args": [],
				"expected": "Hello, World!",
			},
		],
	},
	{
		"id": "w0c2",
		"title": "Add One",
		"mission": "BOOT SEQUENCE — STEP 2",
		"story_pass": (
			"[ Another short test, adding numbers! ]"
		),
		"tests": [
			{
				"call": 'add_one(4)',
				"func": "add_one",
				"args": [4],
				"expected": 5,
			},
			{
				"call": 'add_one(9)',
				"func": "add_one",
				"args": [9],
				"expected": 10,
			},
			{
				"call": 'add_one(-1)',
				"func": "add_one",
				"args": [-1],
				"expected": 0,
			},
		],
	},
	{
		"id": "w0c3",
		"title": "Everything works",
		"mission": "BOOT SEQUENCE — STEP 3",
		"story_pass": (
			"[ Everything is confirmed to be working. ]"
		),
		"tests": [
			{
				"call": 'everything_working()',
				"func": "everything_working",
				"args": [],
				"expected": True,
			},

		],
	},
]
