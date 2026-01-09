import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(__file__)
ANSWER_PATH = os.path.join(BASE_DIR, "data", "unit_answers.json")
RUNNER_PATH = os.path.join(BASE_DIR, "sandbox_runner.py")
EXEC_TIMEOUT_SECONDS = 3


# gets unit info
def get_unit_data(unit_name):
    return ANSWER_KEYS.get(unit_name)


with open(ANSWER_PATH, "r") as f:
    ANSWER_KEYS = json.load(f)


# main method
def evaluate_submission(unit_name, code):
    payload = json.dumps({"unit_name": unit_name, "code": code})
    try:
        result = subprocess.run(
            [sys.executable, RUNNER_PATH],
            input=payload.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=EXEC_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"error": "Your code took too long to run."}

    if result.returncode != 0:
        return {"error": "Code execution failed."}

    try:
        return json.loads(result.stdout.decode("utf-8"))
    except json.JSONDecodeError:
        return {"error": "Invalid response from code runner."}
