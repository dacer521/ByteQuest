import json
import os
import resource
import sys
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import guarded_iter_unpack_sequence, safe_builtins
import operator
import math
import random
import types

BASE_DIR = os.path.dirname(__file__)
ANSWER_PATH = os.path.join(BASE_DIR, "data", "unit_answers.json")

CPU_TIME_SECONDS = 2
MEMORY_LIMIT_BYTES = 128 * 1024 * 1024


# Helper function for in-place operations (+=, -=, etc.)
def _inplacevar_(op, x, y):
    ops = {
        '+=': operator.iadd,
        '-=': operator.isub,
        '*=': operator.imul,
        '/=': operator.itruediv,
        '//=': operator.ifloordiv,
        '%=': operator.imod,
        '**=': operator.ipow,
        '&=': operator.iand,
        '|=': operator.ior,
        '^=': operator.ixor,
        '>>=': operator.irshift,
        '<<=': operator.ilshift,
    }
    return ops.get(op, operator.iadd)(x, y)


# Helper function for subscript assignment (list[i] = value)
def _write_(obj):
    """Guard function that allows writing to objects like lists and dicts"""
    return obj


# Helper function for subscript reading (list[i])
def _getitem_(obj, index):
    """Guard function that allows reading from objects like lists and dicts"""
    return obj[index]


def apply_limits():
    # Limit CPU time and address space to reduce DoS risk.
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_TIME_SECONDS, CPU_TIME_SECONDS))
    except (ValueError, resource.error):
        pass
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
    except (ValueError, resource.error):
        pass


def load_payload():
    raw = sys.stdin.read()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
def _safe_import(name, *args, **kwargs):
    """Safely import only whitelisted modules"""
    allowed_modules = {"math", "random", "turtle"}
    if name not in allowed_modules:
        raise ImportError(f"Import of {name} is not allowed")
    
    # Get the module from sys.modules or import it
    import sys as sys_module
    if name in sys_module.modules:
        return sys_module.modules[name]
    
    # Import the module
    if name == "math":
        return math
    elif name == "random":
        return random
    elif name == "turtle":
        return turtle
    else:
        raise ImportError(f"Import of {name} is not allowed")


def evaluate(unit_name, code, answer_keys):
    unit_data = answer_keys.get(unit_name)
    if not unit_data:
        return {"error": f"Unit {unit_name} not found"}

    expected_answers = unit_data["answers"]
    captured_answers = []

    def submit_answers(ans1, ans2, ans3):
        captured_answers.extend([ans1, ans2, ans3])

    try:
        byte_code = compile_restricted(code, "<user_code>", "exec")
    except Exception as exc:
        return {"error": f"Code compilation error: {str(exc)}"}

    # Set up restricted globals with necessary guard functions for loops and iteration
    restricted_globals = safe_globals.copy()
    
    # Create a safe builtins dictionary with __import__ support
    safe_builtins_dict = safe_globals.get('__builtins__', {})
    if isinstance(safe_builtins_dict, dict):
        safe_builtins_dict = safe_builtins_dict.copy()
    else:
        safe_builtins_dict = {}
    
    safe_builtins_dict['__import__'] = _safe_import
    restricted_globals['__builtins__'] = safe_builtins_dict
    
    restricted_globals["submit_answers"] = submit_answers
    restricted_globals["_getiter_"] = iter  # Required for for loops and range()
    restricted_globals["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence  # Required for unpacking
    restricted_globals["_inplacevar_"] = _inplacevar_  # Required for in-place operations (+=, -=, etc.)
    restricted_globals["_write_"] = _write_  # Required for subscript assignment (list[i] = value)
    restricted_globals["_getitem_"] = _getitem_  # Required for subscript reading (list[i])
    
    # Allow built-in list operations
    restricted_globals["list"] = list
    
    # Allow safe modules directly
    restricted_globals["math"] = math  # Math module for mathematical operations
    restricted_globals["random"] = random  # Random module for random number generation
    
    restricted_locals = {}

    try:
        exec(byte_code, restricted_globals, restricted_locals)
    except Exception as exc:
        return {"error": f"Error running your code: {str(exc)}"}

    if not captured_answers:
        return {"error": "You didn't call submitAnswers() with 3 arguments"}

    if captured_answers == expected_answers:
        return {
            "success": True,
            "score": unit_data["points"],
            "message": "All correct!",
        }

    return {
        "success": False,
        "score": 0,
        "expected": expected_answers,
        "got": captured_answers,
        "message": "Some answers are incorrect",
    }


def main():
    payload = load_payload()
    if not payload:
        print(json.dumps({"error": "Invalid request payload"}))
        return 1

    try:
        with open(ANSWER_PATH, "r") as handle:
            answer_keys = json.load(handle)
    except OSError:
        print(json.dumps({"error": "Answer key unavailable"}))
        return 1

    apply_limits()
    result = evaluate(payload.get("unit_name"), payload.get("code", ""), answer_keys)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
