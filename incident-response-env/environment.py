import json
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List

from models import Action, Observation, Reward
from tasks.task_easy import EASY_SCENARIO
from tasks.task_medium import MEDIUM_SCENARIO
from tasks.task_hard import HARD_SCENARIO
from graders.grader import grade_easy, grade_medium, grade_hard

# ─── CONSTANTS & METADATA ────────────────────────────────────────────────────────
AVAILABLE_ACTIONS: List[str] = [
    "read_logs", "check_metrics", "check_config",
    "restart_service", "rollback_deploy", "update_config",
    "flush_cache", "run_healthcheck", "close_incident"
]

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "log_detective": EASY_SCENARIO,
    "cascade_finder": MEDIUM_SCENARIO,
    "full_outage": HARD_SCENARIO
}

GRADERS = {
    "log_detective": grade_easy,
    "cascade_finder": grade_medium,
    "full_outage": grade_hard
}

# Centralized metadata for use in both environment limits and FastAPI endpoints
TASK_METADATA: List[Dict[str, Any]] = [
    {"name": "log_detective", "difficulty": "easy", "max_steps": EASY_SCENARIO["max_steps"]},
    {"name": "cascade_finder", "difficulty": "medium", "max_steps": MEDIUM_SCENARIO["max_steps"]},
    {"name": "full_outage", "difficulty": "hard", "max_steps": HARD_SCENARIO["max_steps"]}
]

# ─── CORE ENVIRONMENT ────────────────────────────────────────────────────────────

class IncidentResponseEnv:
    """
    Main environment representing the mock infrastructure for the Hackathon.
    Handles the state transitions, reward propagation, and action execution.
    """
    
    def __init__(self, task_name: str = "log_detective") -> None:
        if task_name not in SCENARIOS:
            raise ValueError(f"Unknown task: {task_name}. Choose from {list(SCENARIOS.keys())}")
            
        self.task_name: str = task_name
        self.scenario: Dict[str, Any] = SCENARIOS[task_name]
        
        # State tracking variables
        self.actions_taken: List[Action] = []
        self.current_status: Dict[str, str] = {}
        self.step_count: int = 0
        self.cumulative_score: float = 0.0
        self.done: bool = False

    def reset(self) -> Observation:
        """
        Resets the environment to its initial mock state and returns the first observation.
        """
        self.actions_taken.clear()
        self.step_count = 0
        self.cumulative_score = 0.0
        self.done = False
        self.current_status = dict(self.scenario["initial_system_status"])

        return Observation(
            timestamp=datetime.now(timezone.utc).isoformat(),
            alerts=list(self.scenario["initial_alerts"]),
            last_action_result="Incident opened. Begin investigation.",
            system_status=dict(self.current_status),
            steps_taken=self.step_count,
            max_steps=self.scenario["max_steps"],
            available_actions=list(AVAILABLE_ACTIONS)
        )

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        """
        Processes an action taken by the AI agent, calculates rewards dynamically, 
        and updates the underlying environment state.
        
        Args:
            action (Action): The structured action chosen by the AI.
            
        Returns:
            Tuple containing the new Observation, Reward instance, done flag, and info dict.
        """
        if self.done:
            raise ValueError("Episode is already done. Call reset() to start a new incident.")

        self.step_count += 1
        self.actions_taken.append(action)

        # 1. Execute action securely and get result string
        result_message: str = self._execute_action(action)

        # 2. Update the background infrastructure status if a correct fix is applied
        self._update_status(action)

        # 3. Calculate dynamic dense reward matching Hackathon constraints
        grader_fn = GRADERS[self.task_name]
        score, breakdown = grader_fn(self.actions_taken, self.current_status)
        
        # DENSE REWARD: award the incremental score gained in this specific step
        step_reward: float = score - self.cumulative_score  
        self.cumulative_score = score

        # 4. Check terminal conditions
        max_steps_reached: bool = self.step_count >= self.scenario["max_steps"]
        incident_closed: bool = (action.action_type == "close_incident")
        self.done = max_steps_reached or incident_closed

        reward = Reward(
            score=round(max(0.0, step_reward), 3),
            reason=result_message,
            partial_credit=breakdown,
            cumulative_score=round(self.cumulative_score, 3)
        )

        obs = Observation(
            timestamp=datetime.now(timezone.utc).isoformat(),
            alerts=self._current_alerts(),
            last_action_result=result_message,
            system_status=dict(self.current_status),
            steps_taken=self.step_count,
            max_steps=self.scenario["max_steps"],
            available_actions=list(AVAILABLE_ACTIONS)
        )

        info_dict: Dict[str, Any] = {
            "steps_taken": self.step_count,
            "cumulative_score": self.cumulative_score,
            "breakdown": breakdown
        }

        return obs, reward, self.done, info_dict

    def state(self) -> Dict[str, Any]:
        """Provides a complete snapshot of the current environment state."""
        return {
            "task_name": self.task_name,
            "step_count": self.step_count,
            "system_status": dict(self.current_status),
            "cumulative_score": self.cumulative_score,
            "done": self.done,
            "actions_taken_count": len(self.actions_taken)
        }

    # ─── INTERNAL HELPERS ────────────────────────────────────────────────────────
    
    def _execute_action(self, action: Action) -> str:
        """
        Maps an incoming AI action to the contextual response required by the task.
        """
        action_type = action.action_type
        target_service = action.service or "unknown"
        
        # Dynamic execution map targeting specific handlers
        action_map = {
            "read_logs": lambda s: f"Logs for {s}:\n" + "\n".join(self.scenario.get("logs", {}).get(s, ["No logs found for this service."])),
            "check_metrics": lambda s: f"Metrics for {s}: {json.dumps(self.scenario.get('metrics', {}).get(s, {'status': 'no data'}))}",
            "check_config": lambda s: f"Config for {s}: {json.dumps(self.scenario.get('configs', {}).get(s, {'status': 'no config'}))}",
            "restart_service": lambda s: f"Restarting {s}... Done. Service restarted successfully.",
            "rollback_deploy": lambda s: f"Rolling back {s} to version {action.version or 'previous'}... Done.",
            "update_config": lambda s: f"Updated config for {s}: {action.key} = {action.value}",
            "flush_cache": lambda s: f"Flushing cache for {s}... Done. Cache cleared.",
            "run_healthcheck": lambda s: self._perform_healthcheck(),
            "close_incident": lambda s: "Incident closed. Final score will be calculated."
        }

        executor = action_map.get(action_type)
        if executor:
            return executor(target_service)
        
        return f"Unknown action: {action_type}"

    def _perform_healthcheck(self) -> str:
        """Helper to generate healthcheck strings cleanly."""
        healthy = [k for k, v in self.current_status.items() if v == "healthy"]
        degraded = [k for k, v in self.current_status.items() if v != "healthy"]
        return f"Health check complete. Healthy: {healthy}. Still degraded: {degraded}"

    def _update_status(self, action: Action) -> None:
        """
        Simulate system recovery when correct fixes are applied based strictly on
        the rules defined for each hardcoded hackathon scenario.
        """
        action_type = action.action_type
        service = action.service

        if self.task_name == "log_detective":
            if action_type == "rollback_deploy" and service == "api-gateway":
                self.current_status["api-gateway"] = "healthy"

        elif self.task_name == "cascade_finder":
            if action_type == "restart_service" and service == "database":
                self.current_status["database"] = "healthy"
                self.current_status["user-service"] = "healthy"
                self.current_status["order-service"] = "healthy"
                self.current_status["api-gateway"] = "healthy"

        elif self.task_name == "full_outage":
            if action_type == "update_config" and service == "lb-prod":
                self.current_status["lb-prod"] = "healthy"
            if action_type == "rollback_deploy" and service == "payment-service":
                self.current_status["payment-service"] = "healthy"
            if action_type == "flush_cache" and service == "dns":
                self.current_status["dns"] = "healthy"

    def _current_alerts(self) -> List[str]:
        """Scans the current status and emits string alerts if components are degraded."""
        degraded_services = [service for service, status in self.current_status.items() if status != "healthy"]
        if not degraded_services:
            return ["All systems nominal. Ready to close incident."]
        return [f"ALERT: {service} is still {self.current_status[service]}" for service in degraded_services]
