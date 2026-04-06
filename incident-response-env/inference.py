"""
MANDATORY BASELINE INFERENCE SCRIPT
- Must be named inference.py and placed in root directory
- Uses OpenAI client (mandatory per hackathon rules)
- Reads credentials from environment variables
"""

import os
import json
import time
from typing import List
from openai import OpenAI
from environment import IncidentResponseEnv
from models import Action

API_KEY = "AIzaSyCLywFeWbY6ncho7hjWGCapGVHdRQzXHzU"
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL_NAME = "gemini-2.5-flash"
BENCHMARK = "incident-response-env"

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY or "AIzaSyCLywFeWbY6ncho7hjWGCapGVHdRQzXHzU"
)

SYSTEM_PROMPT = """You are an expert on-call site reliability engineer (SRE).
You receive production incident alerts and must diagnose and fix them.

AVAILABLE ACTIONS (respond with ONLY valid JSON, no explanation):
- {"action_type": "read_logs", "service": "<service_name>"}
- {"action_type": "check_metrics", "service": "<service_name>"}
- {"action_type": "check_config", "service": "<service_name>"}
- {"action_type": "restart_service", "service": "<service_name>"}
- {"action_type": "rollback_deploy", "service": "<service_name>", "version": "<version>"}
- {"action_type": "update_config", "service": "<service_name>", "key": "<key>", "value": <value>}
- {"action_type": "flush_cache", "service": "<service_name>"}
- {"action_type": "run_healthcheck"}
- {"action_type": "close_incident"}

STRATEGY:
1. Read logs and check metrics BEFORE acting
2. Identify root cause (not just symptoms)
3. Fix in correct dependency order
4. Always run healthcheck after fixes
5. Close the incident when resolved

Respond with ONLY a JSON object. No markdown, no explanation."""


def run_episode(task_name: str) -> float:
    env = IncidentResponseEnv(task_name=task_name)
    obs = env.reset()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    done = False
    
    steps_taken = 0
    score = 0.0
    rewards_list: List[float] = []

    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    while not done:
        user_content = f"""
Current System Status: {json.dumps(obs.system_status)}
Active Alerts: {obs.alerts}
Last Action Result: {obs.last_action_result}
Steps taken: {obs.steps_taken}/{obs.max_steps}

What is your next action?"""

        messages.append({"role": "user", "content": user_content})

        action_error = "null"
        action_str = ""
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=150,
                temperature=0.1
            )
            action_text = response.choices[0].message.content.strip()
            messages.append({"role": "assistant", "content": action_text})

            # Parse action
            # We strip out newlines from the action_str so it fits on one line in STDOUT
            action_str = action_text.replace("\\n", "").replace("\\r", "").replace(" ", "").replace("\\\"", "'")
            
            action_dict = json.loads(action_text)
            action = Action(**action_dict)
            
        except json.JSONDecodeError as e:
            action_error = "ParseError"
            action = Action(action_type="run_healthcheck")
            action_str = "parse_error"
        except Exception as e:
            print("API EXCEPTION:", str(e))
            action_error = "Exception"
            action = Action(action_type="close_incident")
            action_str = "exception"

        try:
            obs, reward, done, info = env.step(action)
            step_reward = reward.score
            score = info["cumulative_score"]
        except Exception as e:
            step_reward = 0.0
            done = True
            action_error = "StepError"

        rewards_list.append(step_reward)
        steps_taken += 1

        print(f"[STEP] step={steps_taken} action={action_str} reward={step_reward:.2f} done={str(done).lower()} error={action_error}", flush=True)
        time.sleep(0.5)  # Rate limiting

    success = score > 0.1 # Example threshold
    rewards_str = ",".join(f"{r:.2f}" for r in rewards_list)
    print(f"[END] success={str(success).lower()} steps={steps_taken} score={score:.3f} rewards={rewards_str}", flush=True)
    return score


if __name__ == "__main__":
    tasks = ["log_detective", "cascade_finder", "full_outage"]
    for task in tasks:
        run_episode(task)
