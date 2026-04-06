from fastapi import FastAPI, HTTPException
from models import Action, Observation, Reward
from environment import IncidentResponseEnv
from typing import Dict, Any

app = FastAPI(
    title="Incident Response OpenEnv",
    description="AI agent acts as on-call engineer diagnosing production outages",
    version="1.0.0"
)

# Store active environments per task
_envs: Dict[str, IncidentResponseEnv] = {}

@app.get("/health")
def health():
    return {"status": "ok", "environment": "incident-response-env"}

@app.post("/reset")
def reset(task_name: str = "log_detective") -> Dict[str, Any]:
    if task_name not in ["log_detective", "cascade_finder", "full_outage"]:
        raise HTTPException(status_code=400, detail=f"Unknown task: {task_name}")
    env = IncidentResponseEnv(task_name=task_name)
    _envs[task_name] = env
    obs = env.reset()
    return obs.model_dump()

@app.post("/step")
def step(action: Action, task_name: str = "log_detective") -> Dict[str, Any]:
    if task_name not in _envs:
        raise HTTPException(status_code=400, detail="Call /reset first")
    env = _envs[task_name]
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs.model_dump(),
        "reward": reward.model_dump(),
        "done": done,
        "info": info
    }

@app.get("/state")
def state(task_name: str = "log_detective") -> Dict[str, Any]:
    if task_name not in _envs:
        raise HTTPException(status_code=400, detail="Call /reset first")
    return _envs[task_name].state()

@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {"name": "log_detective", "difficulty": "easy", "max_steps": 15},
            {"name": "cascade_finder", "difficulty": "medium", "max_steps": 20},
            {"name": "full_outage", "difficulty": "hard", "max_steps": 30}
        ]
    }
