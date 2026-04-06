from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any, List

class Action(BaseModel):
    action_type: Literal[
        "read_logs",
        "check_metrics",
        "check_config",
        "restart_service",
        "rollback_deploy",
        "update_config",
        "flush_cache",
        "run_healthcheck",
        "close_incident"
    ]
    service: Optional[str] = None
    metric: Optional[str] = None
    version: Optional[str] = None
    key: Optional[str] = None
    value: Optional[Any] = None
    lines: Optional[int] = 50

class Observation(BaseModel):
    timestamp: str
    alerts: List[str]
    last_action_result: str
    system_status: Dict[str, str]   # service_name -> "healthy" | "degraded" | "down"
    steps_taken: int
    max_steps: int
    available_actions: List[str]

class Reward(BaseModel):
    score: float                    # Always 0.0 to 1.0
    reason: str
    partial_credit: Dict[str, float]
    cumulative_score: float
