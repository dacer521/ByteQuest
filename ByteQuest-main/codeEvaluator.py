import json
import os
from RestrictedPython import compile_restricted, safe_globals


#gets unit info
def get_unit_data(unit_name):
    return ANSWER_KEYS.get(unit_name)

with open('data/unit_answers.json', 'r') as f:
    ANSWER_KEYS = json.load(f)

#main method
def evaluate_submission(unit_name, code):

    unit_data = ANSWER_KEYS.get(unit_name)
    
    if not unit_data:
        return {"error": f"Unit {unit_name} not found"}
    
    expected_answers = unit_data['answers']
    

    captured_answers = []
    

    def submit_answers(ans1, ans2, ans3):
        captured_answers.extend([ans1, ans2, ans3])
    

    try:
        byte_code = compile_restricted(code, '<user_code>', 'exec')
    except Exception as e:
        return {"error": f"Code compilation error: {str(e)}"}
    

    restricted_globals = safe_globals.copy()
    restricted_globals['submit_answers'] = submit_answers 
    restricted_locals = {}
    
    #runs code without security risk bc restricted python 
    try:
        exec(byte_code, restricted_globals, restricted_locals)
    except Exception as e:
        return {"error": f"Error running your code: {str(e)}"}
    

    if not captured_answers:
        return {"error": "You didn't call submitAnswers() with 3 arguments"}
    

    if captured_answers == expected_answers:
        return {"success": True, "score": unit_data['points'], "message": "All correct!"}
    
    #updates how they do
    else:
        return {
            "success": False, 
            "score": 0,
            "got": captured_answers,
            "message": "Some answers are incorrect"
        }