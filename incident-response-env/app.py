import gradio as gr
from fastapi import FastAPI, HTTPException
from typing import Dict, Any
from pydantic import BaseModel

from models import Action, Observation, Reward
from environment import IncidentResponseEnv, SCENARIOS, TASK_METADATA

class StepResponse(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any]

app = FastAPI(
    title="Incident Response OpenEnv",
    description="AI agent acts as on-call engineer diagnosing production outages",
    version="1.0.0"
)

# Store active environments per task mapping task_name -> IncidentResponseEnv instance
_envs: Dict[str, IncidentResponseEnv] = {}

@app.get("/health")
def health() -> Dict[str, str]:
    """Basic service health check."""
    return {"status": "ok", "environment": "incident-response-env"}

@app.post("/reset", response_model=Observation)
def reset(task_name: str = "log_detective"):
    """
    Initializes or resets a specific task environment and returns the starting observation.
    Must be called before /step to setup the environment state.
    """
    if task_name not in SCENARIOS:
        raise HTTPException(
            status_code=404, 
            detail=f"Unknown task: '{task_name}'. Available tasks: {list(SCENARIOS.keys())}"
        )
        
    env = IncidentResponseEnv(task_name=task_name)
    _envs[task_name] = env
    obs = env.reset()
    
    return obs

@app.post("/step", response_model=StepResponse)
def step(action: Action, task_name: str = "log_detective"):
    """
    Processes an action against the actively loaded environment state.
    Calculates dynamic rewards exactly aligned with Hackathon constraints.
    """
    if task_name not in _envs:
        raise HTTPException(
            status_code=400, 
            detail=f"Environment for '{task_name}' is not initialized. Call /reset first."
        )
        
    try:
        env = _envs[task_name]
        obs, reward, done, info = env.step(action)
    except ValueError as e:
        # Reached when trying to step on a terminated episode natively
        raise HTTPException(status_code=400, detail=str(e))
        
    return StepResponse(
        observation=obs,
        reward=reward,
        done=done,
        info=info
    )

@app.get("/state")
def state(task_name: str = "log_detective") -> Dict[str, Any]:
    """Returns the internal state variables without mutating the environment."""
    if task_name not in _envs:
        raise HTTPException(
            status_code=400, 
            detail=f"Environment for '{task_name}' is not initialized. Call /reset first."
        )
    return _envs[task_name].state()

@app.get("/tasks")
def list_tasks() -> Dict[str, Any]:
    """Returns the available scenarios supported by this backend."""
    return {"tasks": TASK_METADATA}

# --- Gradio UI for Hugging Face Space visibility ---
def demo_reset(task_name):
    env = IncidentResponseEnv(task_name)
    obs = env.reset()
    return json.dumps(obs.model_dump(), indent=2)

import json # needed for indentation in UI
demo = gr.Interface(
    fn=demo_reset,
    inputs=gr.Dropdown(["log_detective", "cascade_finder", "full_outage"], value="log_detective", label="Select Scenario"),
    outputs=gr.Code(label="Initial Observation JSON", language="json"),
    title="🚨 Incident Response OpenEnv",
    description="Select a production incident task below to see the starting alerts and system state. This UI interacts with the same backend API used for the Hackathon evaluation."
)

# Mount Gradio to the FastAPI root
app = gr.mount_gradio_app(app, demo, path="/")
