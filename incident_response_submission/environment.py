import json
import random
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

from models import Action, Observation, Reward
from tasks.task_easy import EASY_SCENARIO
from tasks.task_medium import MEDIUM_SCENARIO
from tasks.task_hard import HARD_SCENARIO
from graders.grader import grade_easy, grade_medium, grade_hard

SCENARIOS = {
    "log_detective": EASY_SCENARIO,
    "cascade_finder": MEDIUM_SCENARIO,
    "full_outage": HARD_SCENARIO
}

GRADERS = {
    "log_detective": grade_easy,
    "cascade_finder": grade_medium,
    "full_outage": grade_hard
}

class IncidentResponseEnv:
    def __init__(self, task_name: str = "log_detective"):
        assert task_name in SCENARIOS, f"Unknown task: {task_name}. Choose from {list(SCENARIOS.keys())}"
        self.task_name = task_name
        self.scenario = SCENARIOS[task_name]
        self.actions_taken = []
        self.current_status = {}
        self.step_count = 0
        self.cumulative_score = 0.0
        self.done = False

    def reset(self) -> Observation:
        self.actions_taken = []
        self.step_count = 0
        self.cumulative_score = 0.0
        self.done = False
        self.current_status = self.scenario["initial_system_status"].copy()

        return Observation(
            timestamp=datetime.now(timezone.utc).isoformat(),
            alerts=self.scenario["initial_alerts"],
            last_action_result="Incident opened. Begin investigation.",
            system_status=self.current_status,
            steps_taken=0,
            max_steps=self.scenario["max_steps"],
            available_actions=[
                "read_logs", "check_metrics", "check_config",
                "restart_service", "rollback_deploy", "update_config",
                "flush_cache", "run_healthcheck", "close_incident"
            ]
        )

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict]:
        if self.done:
            raise ValueError("Episode is done. Call reset() first.")

        self.step_count += 1
        self.actions_taken.append(action)

        # Execute action and get result string
        result = self._execute_action(action)

        # Update system status based on correct fixes applied
        self._update_status(action)

        # Calculate reward
        grader_fn = GRADERS[self.task_name]
        score, breakdown = grader_fn(self.actions_taken, self.current_status)
        step_reward = score - self.cumulative_score  # DENSE: reward for improvement this step
        self.cumulative_score = score

        # Check done conditions
        max_steps_reached = self.step_count >= self.scenario["max_steps"]
        incident_closed = action.action_type == "close_incident"
        self.done = max_steps_reached or incident_closed

        reward = Reward(
            score=round(max(0.0, step_reward), 3),
            reason=result,
            partial_credit=breakdown,
            cumulative_score=round(self.cumulative_score, 3)
        )

        obs = Observation(
            timestamp=datetime.now(timezone.utc).isoformat(),
            alerts=self._current_alerts(),
            last_action_result=result,
            system_status=self.current_status,
            steps_taken=self.step_count,
            max_steps=self.scenario["max_steps"],
            available_actions=["read_logs", "check_metrics", "check_config",
                               "restart_service", "rollback_deploy", "update_config",
                               "flush_cache", "run_healthcheck", "close_incident"]
        )

        return obs, reward, self.done, {
            "steps_taken": self.step_count,
            "cumulative_score": self.cumulative_score,
            "breakdown": breakdown
        }

    def state(self) -> Dict[str, Any]:
        return {
            "task_name": self.task_name,
            "step_count": self.step_count,
            "system_status": self.current_status,
            "cumulative_score": self.cumulative_score,
            "done": self.done,
            "actions_taken_count": len(self.actions_taken)
        }

    def _execute_action(self, action: Action) -> str:
        t = action.action_type
        s = action.service or "unknown"

        if t == "read_logs":
            logs = self.scenario.get("logs", {}).get(s, ["No logs found for this service."])
            return f"Logs for {s}:\n" + "\n".join(logs)

        elif t == "check_metrics":
            metrics = self.scenario.get("metrics", {}).get(s, {"status": "no data"})
            return f"Metrics for {s}: {json.dumps(metrics)}"

        elif t == "check_config":
            config = self.scenario.get("configs", {}).get(s, {"status": "no config"})
            return f"Config for {s}: {json.dumps(config)}"

        elif t == "restart_service":
            return f"Restarting {s}... Done. Service restarted successfully."

        elif t == "rollback_deploy":
            version = action.version or "previous"
            return f"Rolling back {s} to version {version}... Done."

        elif t == "update_config":
            return f"Updated config for {s}: {action.key} = {action.value}"

        elif t == "flush_cache":
            return f"Flushing cache for {s}... Done. Cache cleared."

        elif t == "run_healthcheck":
            healthy = [k for k, v in self.current_status.items() if v == "healthy"]
            degraded = [k for k, v in self.current_status.items() if v != "healthy"]
            return f"Health check complete. Healthy: {healthy}. Still degraded: {degraded}"

        elif t == "close_incident":
            return f"Incident closed. Final score will be calculated."

        return f"Unknown action: {t}"

    def _update_status(self, action: Action):
        """Simulate system recovery when correct fixes are applied"""
        sc = self.scenario
        t = action.action_type
        s = action.service

        if self.task_name == "log_detective":
            if t == "rollback_deploy" and s == "api-gateway":
                self.current_status["api-gateway"] = "healthy"

        elif self.task_name == "cascade_finder":
            if t == "restart_service" and s == "database":
                self.current_status["database"] = "healthy"
                self.current_status["user-service"] = "healthy"
                self.current_status["order-service"] = "healthy"
                self.current_status["api-gateway"] = "healthy"

        elif self.task_name == "full_outage":
            if t == "update_config" and s == "lb-prod":
                self.current_status["lb-prod"] = "healthy"
            if t == "rollback_deploy" and s == "payment-service":
                self.current_status["payment-service"] = "healthy"
            if t == "flush_cache" and s == "dns":
                self.current_status["dns"] = "healthy"

    def _current_alerts(self):
        degraded = [k for k, v in self.current_status.items() if v != "healthy"]
        if not degraded:
            return ["All systems nominal. Ready to close incident."]
        return [f"ALERT: {svc} is still {self.current_status[svc]}" for svc in degraded]
