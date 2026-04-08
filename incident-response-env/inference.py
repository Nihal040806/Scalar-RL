"""
Inference Script — MANDATORY BASELINE
=====================================
STDOUT FORMAT (auto-grader parses these exact lines):
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import os
import json
import time
from typing import List, Optional
from openai import OpenAI
from environment import IncidentResponseEnv
from models import Action

# ── Credentials (read strictly from env vars defined by OpenEnv rules) ──
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
BENCHMARK = "incident-response-env"

if HF_TOKEN is None:
    print("WARNING: HF_TOKEN not found. Baseline evaluation will likely fail.", flush=True)

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN,
    timeout=60.0,  # 60s timeout so it never hangs
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


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    # MANDATORY FORMAT: [END] success= steps= rewards=
    print(f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}", flush=True)


def call_llm(messages: list, max_retries: int = 3) -> str:
    """Call LLM with retry + backoff for rate limits."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=150,
                temperature=0.1
            )
            text = (response.choices[0].message.content or "").strip()
            # Strip markdown code fences if model wraps its answer
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]  # remove first line
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0].strip()
            return text
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                # Rate limited — wait and retry
                wait = 15 * (attempt + 1)
                time.sleep(wait)
                continue
            raise  # re-raise non-rate-limit errors
    raise RuntimeError("Max retries exceeded for LLM call")


def run_episode(task_name: str) -> float:
    env = IncidentResponseEnv(task_name=task_name)
    obs = env.reset()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    done = False

    steps_taken = 0
    score = 0.0
    rewards_list: List[float] = []

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    while not done:
        user_content = (
            f"Current System Status: {json.dumps(obs.system_status)}\n"
            f"Active Alerts: {obs.alerts}\n"
            f"Last Action Result: {obs.last_action_result}\n"
            f"Steps taken: {obs.steps_taken}/{obs.max_steps}\n\n"
            f"What is your next action?"
        )
        messages.append({"role": "user", "content": user_content})

        action_error: Optional[str] = None
        action_str = ""
        try:
            action_text = call_llm(messages)
            messages.append({"role": "assistant", "content": action_text})

            # Clean action_str for single-line STDOUT
            action_str = action_text.replace("\n", "").replace("\r", "").replace(" ", "")

            action_dict = json.loads(action_text)
            action = Action(**action_dict)

        except json.JSONDecodeError:
            action_error = "ParseError"
            action = Action(action_type="run_healthcheck")
            action_str = "parse_error"
        except Exception:
            action_error = "Exception"
            action = Action(action_type="close_incident")
            action_str = "exception"

        try:
            obs, reward, done, info = env.step(action)
            step_reward = reward.score
            score = info["cumulative_score"]
        except Exception:
            step_reward = 0.0
            done = True
            action_error = "StepError"

        rewards_list.append(step_reward)
        steps_taken += 1

        log_step(step=steps_taken, action=action_str, reward=step_reward, done=done, error=action_error)

        # Rate-limit pause (reduced to 12s for faster audit completion)
        time.sleep(12)

    success = score > 0.1
    log_end(success=success, steps=steps_taken, score=score, rewards=rewards_list)
    return score


if __name__ == "__main__":
    tasks = ["log_detective", "cascade_finder", "full_outage"]
    for task in tasks:
        run_episode(task)
