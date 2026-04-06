# 🚨 On-Call Incident Response Debugger — MASTER PROJECT SPECIFICATION
## OpenEnv Hackathon (Scaler × Meta) | Submission Deadline: April 8th, 11:59 PM

---

## 📌 WHAT YOU ARE BUILDING

You are building an **OpenEnv environment** — NOT an AI agent.
Think of it as building a gym/arena. The judges plug their own AI agent into your world and test it.

```
You build  →  The incident response simulation world
Judges plug →  Their AI agent (Nemotron 3 Super) into your world
They measure → How well their agent diagnoses and fixes outages in your world
```

Your environment must expose exactly 3 API endpoints:
- `POST /reset`  → Start a fresh incident scenario, return initial observation
- `POST /step`   → Agent takes an action, world responds with new observation + reward
- `GET /state`   → Return current state of the environment

---

## 🏆 WHY THIS TRACK WINS

| Criteria | Weight | Why You Score Max |
|---|---|---|
| Real-world utility | 30% | Every software engineer does incident response. Meta judges live this daily. |
| Task & grader quality | 25% | Each outage has exactly one root cause — 100% deterministic grading |
| Environment design | 20% | Natural dense rewards at every step (read → diagnose → fix → verify) |
| Code quality | 15% | Clean OpenEnv spec, typed Pydantic models, Docker works |
| Creativity & novelty | 10% | Nobody has built this in OpenEnv. Guaranteed novel. |
| **PROJECTED TOTAL** | **100%** | **~92-95/100** |

---

## 📁 COMPLETE PROJECT STRUCTURE

```
incident-response-env/
│
├── environment.py              # Core OpenEnv class (step/reset/state)
├── models.py                   # Pydantic typed models (Action/Observation/Reward)
├── app.py                      # FastAPI wrapper for HF Space deployment
├── inference.py                # Baseline script (MANDATORY - uses OpenAI client)
├── openenv.yaml                # OpenEnv metadata spec file
├── Dockerfile                  # Container for HF Space
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation (mandatory)
│
├── tasks/
│   ├── __init__.py
│   ├── task_easy.py            # Task 1: log_detective
│   ├── task_medium.py          # Task 2: cascade_finder
│   └── task_hard.py            # Task 3: full_outage
│
├── graders/
│   ├── __init__.py
│   └── grader.py               # All scoring logic (returns 0.0 to 1.0)
│
├── data/
│   ├── scenarios/
│   │   ├── easy_001.json       # Synthetic easy scenario
│   │   ├── easy_002.json
│   │   ├── medium_001.json     # Synthetic medium scenario
│   │   ├── medium_002.json
│   │   ├── hard_001.json       # Synthetic hard scenario
│   │   └── hard_002.json
│   └── generate_scenarios.py   # Script to generate more synthetic data
│
└── tests/
    └── test_environment.py     # Basic sanity tests
```

---

## 📋 COMPLETE CODE — EVERY FILE

---

### FILE 1: `requirements.txt`

```
fastapi==0.110.0
uvicorn==0.29.0
pydantic==2.6.4
openai==1.14.0
pyyaml==6.0.1
pytest==8.1.0
httpx==0.27.0
```

---

### FILE 2: `models.py`

```python
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
    system_status: Dict[str, str]   # service_name → "healthy" | "degraded" | "down"
    steps_taken: int
    max_steps: int
    available_actions: List[str]

class Reward(BaseModel):
    score: float                    # Always 0.0 to 1.0
    reason: str
    partial_credit: Dict[str, float]
    cumulative_score: float
```

---

### FILE 3: `tasks/task_easy.py`

```python
# TASK: log_detective
# DIFFICULTY: Easy
# SCENARIO: Web server returning 500 errors after a bad deploy
# ROOT CAUSE: api-gateway deployed v2.4.0 which has NullPointerException bug
# SOLUTION: read_logs → identify api-gateway → rollback_deploy → run_healthcheck

EASY_SCENARIO = {
    "task_name": "log_detective",
    "difficulty": "easy",
    "description": "A web server is returning 500 errors. Diagnose and fix.",
    "initial_alerts": [
        "CRITICAL: api-gateway 500 error rate at 45% (threshold: 1%)",
        "WARNING: User login failures spiking — 320 errors in last 5 minutes"
    ],
    "initial_system_status": {
        "api-gateway": "degraded",
        "database": "healthy",
        "cache": "healthy",
        "auth-service": "healthy"
    },
    "logs": {
        "api-gateway": [
            "[ERROR] NullPointerException at UserController.java:142",
            "[ERROR] Failed to parse null userId from request headers",
            "[ERROR] NullPointerException at UserController.java:142",
            "[INFO]  Deploy v2.4.0 completed at 02:47 AM",
            "[INFO]  Previous version: v2.3.1",
            "[ERROR] NullPointerException at UserController.java:142",
        ],
        "database": ["[INFO] All queries nominal. Latency avg 12ms"],
        "cache": ["[INFO] Cache hit rate 94%. No issues."],
        "auth-service": ["[INFO] Auth service healthy."]
    },
    "metrics": {
        "api-gateway": {"error_rate": "45%", "cpu": "22%", "memory": "61%"},
        "database": {"connections": "45/200", "cpu": "12%", "memory": "40%"},
        "cache": {"hit_rate": "94%", "cpu": "5%"}
    },
    "configs": {
        "api-gateway": {"version": "v2.4.0", "replicas": 3, "max_timeout": 30}
    },
    # Ground truth for grader
    "root_cause": "bad_deploy",
    "root_cause_service": "api-gateway",
    "correct_fix_action": "rollback_deploy",
    "correct_fix_service": "api-gateway",
    "correct_rollback_version": "v2.3.1",
    "max_steps": 15
}
```

---

### FILE 4: `tasks/task_medium.py`

```python
# TASK: cascade_finder
# DIFFICULTY: Medium
# SCENARIO: Database connection pool exhausted → 3 microservices failing in cascade
# ROOT CAUSE: database connection pool maxed out (traffic spike + no auto-scaling)
# SOLUTION: check_metrics:database → update_config:max_connections → restart_service:database → run_healthcheck
# KEY CHALLENGE: Must identify ROOT service (database), not just the downstream victims

MEDIUM_SCENARIO = {
    "task_name": "cascade_finder",
    "difficulty": "medium",
    "description": (
        "Multiple services are failing. A cascade failure is occurring. "
        "Find the root cause service and fix it in the correct order."
    ),
    "initial_alerts": [
        "CRITICAL: api-gateway - 503 Service Unavailable (error rate 78%)",
        "CRITICAL: user-service - Cannot connect to database (timeout)",
        "CRITICAL: order-service - Cannot connect to database (timeout)",
        "WARNING: database - Connection pool utilization at 100%"
    ],
    "initial_system_status": {
        "api-gateway": "degraded",
        "user-service": "down",
        "order-service": "down",
        "database": "degraded",   # ROOT CAUSE
        "cache": "healthy"
    },
    "logs": {
        "api-gateway": [
            "[ERROR] Upstream user-service timeout after 30s",
            "[ERROR] Upstream order-service timeout after 30s",
            "[INFO]  Retrying failed requests (attempt 3/3)"
        ],
        "user-service": [
            "[ERROR] HikariPool-1 - Connection is not available, request timed out after 30000ms",
            "[ERROR] Unable to acquire JDBC Connection",
            "[ERROR] Database connection pool exhausted"
        ],
        "order-service": [
            "[ERROR] Cannot get a connection, pool error Timeout waiting for connection",
            "[ERROR] Database connection pool exhausted"
        ],
        "database": [
            "[WARN]  Max connections reached: 100/100",
            "[WARN]  New connection requests queuing (queue depth: 47)",
            "[INFO]  Traffic spike detected: 3x normal load since 03:15 AM"
        ]
    },
    "metrics": {
        "database": {"connections": "100/100", "cpu": "89%", "memory": "78%", "queue_depth": 47},
        "api-gateway": {"error_rate": "78%", "cpu": "45%"},
        "user-service": {"error_rate": "100%", "db_timeout_count": 312},
        "order-service": {"error_rate": "100%", "db_timeout_count": 198}
    },
    "configs": {
        "database": {"max_connections": 100, "pool_timeout": 30, "version": "postgres-14"}
    },
    # Ground truth
    "root_cause": "connection_pool_exhausted",
    "root_cause_service": "database",
    "correct_fix_sequence": [
        ("check_metrics", "database"),
        ("update_config", "database"),   # must update config BEFORE restart
        ("restart_service", "database"), # apply config changes
        ("run_healthcheck", None)        # verify cascade recovery
    ],
    "correct_config_key": "max_connections",
    "correct_config_value": 300,
    "max_steps": 20
}
```

---

### FILE 5: `tasks/task_hard.py`

```python
# TASK: full_outage
# DIFFICULTY: Hard
# SCENARIO: 3 simultaneous interacting issues causing full production outage
# ISSUES:
#   1. Load balancer misconfigured (P0) - MUST fix first or service restarts don't help
#   2. Payment service memory leak (P1) - fix second
#   3. Stale DNS cache (P1) - fix last (or traffic still won't route correctly)
# KEY CHALLENGE: Issues INTERACT — fixing in wrong order wastes steps and costs score

HARD_SCENARIO = {
    "task_name": "full_outage",
    "difficulty": "hard",
    "description": (
        "Full production outage. Multiple root causes interacting. "
        "Triage by severity, fix in dependency order, verify recovery."
    ),
    "initial_alerts": [
        "P0 CRITICAL: lb-prod - Health checks failing for all backend instances",
        "P1 CRITICAL: payment-service - Memory usage at 98%, OOMKilled 3 times in 1hr",
        "P1 CRITICAL: payment-service - Pod restart loop detected (CrashLoopBackOff)",
        "P1 WARNING:  dns - Stale cache entries detected for payment.internal",
        "P2 WARNING:  api-gateway - Elevated latency (avg 8400ms, threshold 500ms)"
    ],
    "initial_system_status": {
        "lb-prod": "down",              # P0 - fix first
        "payment-service": "down",      # P1 - fix second
        "dns": "degraded",              # P1 - fix third
        "api-gateway": "degraded",
        "database": "healthy",
        "cache": "healthy"
    },
    "logs": {
        "lb-prod": [
            "[ERROR] Health check failed: GET /health → Connection refused",
            "[ERROR] All backend instances marked unhealthy",
            "[INFO]  Config last modified: 03:58 AM (deployment script)",
            "[WARN]  max_connections set to 1 (was 500) — possible config error"
        ],
        "payment-service": [
            "[ERROR] OOMKilled: memory limit 512Mi exceeded",
            "[ERROR] java.lang.OutOfMemoryError: Java heap space",
            "[INFO]  Heap dump analysis: RetryBuffer holding 2.1M uncleaned objects",
            "[WARN]  Memory leak in RetryBuffer — fix: restart with -Xmx768m or patch v3.1.2"
        ],
        "dns": [
            "[WARN]  Cached entry for payment.internal points to old IP 10.0.1.45",
            "[INFO]  Actual payment-service IP: 10.0.2.88 (updated after restart)",
            "[INFO]  TTL expired 47 minutes ago — manual flush required"
        ]
    },
    "metrics": {
        "lb-prod": {"healthy_backends": "0/6", "max_connections": 1, "config_version": "broken"},
        "payment-service": {"memory_usage": "98%", "restart_count": 3, "status": "CrashLoopBackOff"},
        "dns": {"stale_entries": 1, "affected_service": "payment.internal"}
    },
    "configs": {
        "lb-prod": {"max_connections": 1, "health_check_path": "/health", "backend_pool": "payment-service"},
        "payment-service": {"memory_limit": "512Mi", "version": "v3.1.0", "latest_stable": "v3.1.2"}
    },
    # Ground truth — ORDER MATTERS for scoring
    "root_causes": {
        "lb-prod": {"type": "misconfigured_max_connections", "severity": "P0"},
        "payment-service": {"type": "memory_leak", "severity": "P1"},
        "dns": {"type": "stale_cache", "severity": "P1"}
    },
    "correct_fix_order": ["lb-prod", "payment-service", "dns"],
    "correct_fixes": {
        "lb-prod": {"action": "update_config", "key": "max_connections", "value": 500},
        "payment-service": {"action": "rollback_deploy", "version": "v3.1.2"},
        "dns": {"action": "flush_cache", "service": "dns"}
    },
    "max_steps": 30
}
```

---

### FILE 6: `graders/grader.py`

```python
from typing import List, Tuple, Dict
from models import Action

def grade_easy(actions_taken: List[Action], final_status: Dict) -> Tuple[float, Dict]:
    """
    Grader for log_detective (easy task)
    Max score: 1.0
    Partial credits:
        0.20 - Read logs for any service
        0.30 - Identified correct root cause service (api-gateway)
        0.30 - Applied rollback action on api-gateway
        0.10 - Healthcheck performed AFTER the fix
        0.10 - Closed incident as final action
    """
    score = 0.0
    breakdown = {}

    action_types = [a.action_type for a in actions_taken]
    services = [a.service for a in actions_taken]

    # +0.20 — Read logs (any service)
    if "read_logs" in action_types:
        score += 0.20
        breakdown["read_logs"] = 0.20

    # +0.30 — Identified api-gateway as the problem
    if "api-gateway" in services:
        score += 0.30
        breakdown["identified_service"] = 0.30

    # +0.30 — Applied rollback on api-gateway
    rollback_on_correct = any(
        a.action_type == "rollback_deploy" and a.service == "api-gateway"
        for a in actions_taken
    )
    if rollback_on_correct:
        score += 0.30
        breakdown["applied_fix"] = 0.30

    # +0.10 — Healthcheck AFTER rollback
    if "rollback_deploy" in action_types and "run_healthcheck" in action_types:
        rollback_idx = action_types.index("rollback_deploy")
        health_idx = action_types.index("run_healthcheck")
        if health_idx > rollback_idx:
            score += 0.10
            breakdown["verified_fix"] = 0.10

    # +0.10 — Closed incident properly
    if action_types and action_types[-1] == "close_incident":
        score += 0.10
        breakdown["closed_incident"] = 0.10

    return round(min(score, 1.0), 3), breakdown


def grade_medium(actions_taken: List[Action], final_status: Dict) -> Tuple[float, Dict]:
    """
    Grader for cascade_finder (medium task)
    Max score: 1.0
    KEY: Rewards finding ROOT CAUSE (database), not just fixing downstream victims
    Partial credits:
        0.25 - Checked metrics/logs for database (root cause)
        0.25 - Updated database config (max_connections) before restart
        0.25 - Restarted database AFTER config update (order matters!)
        0.15 - Ran healthcheck to verify cascade recovery
        0.10 - Closed incident
    """
    score = 0.0
    breakdown = {}

    action_pairs = [(a.action_type, a.service) for a in actions_taken]
    action_types = [a.action_type for a in actions_taken]

    # +0.25 — Investigated database (root cause)
    investigated_db = any(
        s == "database" and t in ("check_metrics", "read_logs", "check_config")
        for t, s in action_pairs
    )
    if investigated_db:
        score += 0.25
        breakdown["identified_root_cause"] = 0.25

    # +0.25 — Config updated BEFORE restart (order constraint)
    config_indices = [i for i, (t, s) in enumerate(action_pairs)
                      if t == "update_config" and s == "database"]
    restart_indices = [i for i, (t, s) in enumerate(action_pairs)
                       if t == "restart_service" and s == "database"]

    if config_indices and restart_indices:
        if min(config_indices) < min(restart_indices):
            score += 0.25
            breakdown["correct_fix_order"] = 0.25

    # +0.25 — Restarted database
    if ("restart_service", "database") in action_pairs:
        score += 0.25
        breakdown["restarted_db"] = 0.25

    # +0.15 — Verified recovery
    if "run_healthcheck" in action_types:
        score += 0.15
        breakdown["verified_recovery"] = 0.15

    # +0.10 — Closed properly
    if action_types and action_types[-1] == "close_incident":
        score += 0.10
        breakdown["closed_incident"] = 0.10

    return round(min(score, 1.0), 3), breakdown


def grade_hard(actions_taken: List[Action], final_status: Dict) -> Tuple[float, Dict]:
    """
    Grader for full_outage (hard task)
    Max score: 1.0
    KEY: 3 issues must be fixed. Bonus for correct priority order (P0 first)
    Partial credits:
        0.15 - Fixed lb-prod (P0 issue — update max_connections)
        0.15 - Fixed payment-service (rollback to v3.1.2)
        0.15 - Fixed dns (flush_cache)
        0.20 - Fixed in correct priority order (lb → payment → dns)
        0.15 - Triaged all issues before fixing (read before acting)
        0.10 - Ran healthcheck after all fixes
        0.10 - Closed incident
    """
    score = 0.0
    breakdown = {}

    action_pairs = [(a.action_type, a.service) for a in actions_taken]
    action_types = [a.action_type for a in actions_taken]

    # +0.15 each fix applied
    lb_fixed = any(
        t == "update_config" and s == "lb-prod"
        for t, s in action_pairs
    )
    payment_fixed = any(
        t == "rollback_deploy" and s == "payment-service"
        for t, s in action_pairs
    )
    dns_fixed = any(
        t == "flush_cache" and s == "dns"
        for t, s in action_pairs
    )

    if lb_fixed:
        score += 0.15
        breakdown["fixed_lb"] = 0.15
    if payment_fixed:
        score += 0.15
        breakdown["fixed_payment"] = 0.15
    if dns_fixed:
        score += 0.15
        breakdown["fixed_dns"] = 0.15

    # +0.20 — Correct priority order (lb before payment before dns)
    if lb_fixed and payment_fixed and dns_fixed:
        lb_idx = next(i for i, (t, s) in enumerate(action_pairs) if t == "update_config" and s == "lb-prod")
        pay_idx = next(i for i, (t, s) in enumerate(action_pairs) if t == "rollback_deploy" and s == "payment-service")
        dns_idx = next(i for i, (t, s) in enumerate(action_pairs) if t == "flush_cache" and s == "dns")
        if lb_idx < pay_idx < dns_idx:
            score += 0.20
            breakdown["correct_priority_order"] = 0.20

    # +0.15 — Investigated before acting (read logs/metrics before first fix)
    first_fix_idx = next(
        (i for i, (t, _) in enumerate(action_pairs)
         if t in ("update_config", "rollback_deploy", "flush_cache", "restart_service")),
        len(action_pairs)
    )
    investigated_before_fix = any(
        t in ("read_logs", "check_metrics", "check_config")
        for t, _ in action_pairs[:first_fix_idx]
    )
    if investigated_before_fix:
        score += 0.15
        breakdown["investigated_first"] = 0.15

    # +0.10 — Healthcheck after all fixes
    if "run_healthcheck" in action_types:
        last_fix_idx = max(
            [i for i, (t, _) in enumerate(action_pairs)
             if t in ("update_config", "rollback_deploy", "flush_cache")],
            default=-1
        )
        health_idx = max(i for i, t in enumerate(action_types) if t == "run_healthcheck")
        if health_idx > last_fix_idx:
            score += 0.10
            breakdown["verified_after_all_fixes"] = 0.10

    # +0.10 — Proper close
    if action_types and action_types[-1] == "close_incident":
        score += 0.10
        breakdown["closed_incident"] = 0.10

    return round(min(score, 1.0), 3), breakdown
```

---

### FILE 7: `environment.py`

```python
import json
import random
from datetime import datetime
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
            timestamp=datetime.utcnow().isoformat(),
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
            timestamp=datetime.utcnow().isoformat(),
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
```

---

### FILE 8: `app.py`

```python
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
```

---

### FILE 9: `inference.py` ⚠️ MANDATORY

```python
"""
MANDATORY BASELINE INFERENCE SCRIPT
- Must be named inference.py and placed in root directory
- Uses OpenAI client (mandatory per hackathon rules)
- Reads credentials from environment variables
- Produces reproducible scores on all 3 tasks
- Runtime target: < 20 minutes on vcpu=2, memory=8gb
"""

import os
import json
import time
from openai import OpenAI
from environment import IncidentResponseEnv
from models import Action

# MANDATORY: Read from environment variables
client = OpenAI(
    base_url=os.environ.get("API_BASE_URL", "https://api.openai.com/v1"),
    api_key=os.environ.get("HF_TOKEN", "your-key-here")
)
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")

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
    final_score = 0.0

    print(f"\n{'='*50}")
    print(f"Task: {task_name}")
    print(f"Initial alerts: {obs.alerts}")
    print(f"{'='*50}")

    while not done:
        user_content = f"""
Current System Status: {json.dumps(obs.system_status)}
Active Alerts: {obs.alerts}
Last Action Result: {obs.last_action_result}
Steps taken: {obs.steps_taken}/{obs.max_steps}

What is your next action?"""

        messages.append({"role": "user", "content": user_content})

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
            action_dict = json.loads(action_text)
            action = Action(**action_dict)

        except json.JSONDecodeError:
            print(f"  [PARSE ERROR] Could not parse: {action_text}")
            action = Action(action_type="run_healthcheck")
        except Exception as e:
            print(f"  [ERROR] {e}")
            action = Action(action_type="close_incident")

        obs, reward, done, info = env.step(action)
        final_score = info["cumulative_score"]
        print(f"  Step {obs.steps_taken}: {action.action_type}({action.service or ''}) → reward: {reward.score:.3f} | cumulative: {final_score:.3f}")

        time.sleep(0.5)  # Rate limiting

    print(f"  FINAL SCORE for {task_name}: {final_score:.3f}")
    return final_score


if __name__ == "__main__":
    print("Running baseline inference on all 3 tasks...")
    print(f"Model: {MODEL_NAME}")
    print(f"API Base: {os.environ.get('API_BASE_URL', 'default')}")

    results = {}
    tasks = ["log_detective", "cascade_finder", "full_outage"]

    for task in tasks:
        score = run_episode(task)
        results[task] = round(score, 3)

    print(f"\n{'='*50}")
    print("BASELINE SCORES:")
    for task, score in results.items():
        print(f"  {task}: {score:.3f}")
    print(f"  Average: {sum(results.values()) / len(results):.3f}")
    print(f"{'='*50}")

    # Save results
    with open("baseline_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results saved to baseline_results.json")
```

---

### FILE 10: `openenv.yaml`

```yaml
name: incident-response-env
version: 1.0.0
description: >
  A production incident response simulation environment.
  An AI agent acts as an on-call SRE engineer, receiving real-time
  alerts, reading logs and metrics, diagnosing root causes, and
  applying fixes in the correct order to restore system health.
author: your-huggingface-username
tags:
  - openenv
  - devops
  - incident-response
  - site-reliability
  - real-world

tasks:
  - name: log_detective
    difficulty: easy
    max_steps: 15
    description: >
      A web server returns 500 errors after a recent deployment.
      Agent must read logs, identify the faulty service, and rollback.
    expected_score_random: 0.15
    expected_score_baseline: 0.72

  - name: cascade_finder
    difficulty: medium
    max_steps: 20
    description: >
      A database connection pool exhaustion causes cascading failures
      across 3 microservices. Agent must trace to root cause, fix
      configuration, and verify downstream recovery. Order matters.
    expected_score_random: 0.08
    expected_score_baseline: 0.58

  - name: full_outage
    difficulty: hard
    max_steps: 30
    description: >
      Full production outage caused by 3 simultaneous interacting issues:
      misconfigured load balancer (P0), memory leak (P1), stale DNS (P1).
      Agent must triage by severity and fix in dependency order.
    expected_score_random: 0.03
    expected_score_baseline: 0.34

observation_space:
  type: object
  fields:
    - name: alerts
      type: array[string]
      description: Active system alerts
    - name: system_status
      type: object
      description: Map of service_name to health status
    - name: last_action_result
      type: string
      description: Output from the last action taken
    - name: steps_taken
      type: integer
    - name: max_steps
      type: integer

action_space:
  type: discrete_structured
  actions:
    - read_logs
    - check_metrics
    - check_config
    - restart_service
    - rollback_deploy
    - update_config
    - flush_cache
    - run_healthcheck
    - close_incident

reward:
  range: [0.0, 1.0]
  type: dense
  description: >
    Partial credit awarded at every meaningful diagnostic or fix step.
    Rewards correct identification of root cause, correct fix actions,
    correct ordering, verification via healthcheck, and proper close.
```

---

### FILE 11: `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

---

### FILE 12: `README.md`

```markdown
# 🚨 Incident Response OpenEnv

An OpenEnv environment where an AI agent plays the role of an
on-call SRE engineer diagnosing and fixing production outages.

## Environment Description

The agent receives production alerts, reads logs and metrics,
identifies root causes, and applies fixes — in the correct order.
The environment rewards partial progress: reading the right logs,
identifying the correct root cause, applying the fix, and verifying recovery.

## Why This Matters

Incident response is one of the most universal tasks in software engineering.
Every company with a production system deals with this daily.
Training agents to do this well has immediate real-world value.

## Setup & Installation

```bash
# Local
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 7860

# Docker
docker build -t incident-response-env .
docker run -p 7860:7860 incident-response-env
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| /health | GET | Health check |
| /reset?task_name=log_detective | POST | Start new episode |
| /step?task_name=log_detective | POST | Take an action |
| /state?task_name=log_detective | GET | Get current state |
| /tasks | GET | List all tasks |

## Action Space

| Action | Parameters | Description |
|---|---|---|
| read_logs | service | Read recent logs for a service |
| check_metrics | service | Get current metrics |
| check_config | service | Read current configuration |
| restart_service | service | Restart a service |
| rollback_deploy | service, version | Roll back to a previous version |
| update_config | service, key, value | Update a configuration value |
| flush_cache | service | Flush service cache |
| run_healthcheck | — | Check all service health |
| close_incident | — | Close the incident (ends episode) |

## Tasks

| Task | Difficulty | Max Steps | Description |
|---|---|---|---|
| log_detective | Easy | 15 | Single service outage from bad deploy |
| cascade_finder | Medium | 20 | Cascading failure across microservices |
| full_outage | Hard | 30 | 3 simultaneous interacting root causes |

## Observation Space

```json
{
  "timestamp": "2024-04-07T03:15:00Z",
  "alerts": ["CRITICAL: api-gateway 500 error rate 45%"],
  "last_action_result": "Logs for api-gateway: [ERROR] NullPointerException...",
  "system_status": {"api-gateway": "degraded", "database": "healthy"},
  "steps_taken": 2,
  "max_steps": 15,
  "available_actions": ["read_logs", "check_metrics", ...]
}
```

## Reward Function

Dense rewards — partial credit at every meaningful step:
- Investigating the correct service: +0.20 to +0.30
- Applying the correct fix: +0.25 to +0.40
- Correct ordering (config before restart): +0.20 to +0.25
- Verifying with healthcheck: +0.10 to +0.15
- Closing properly: +0.10

## Baseline Scores

| Task | Random Agent | Baseline LLM | Strong Agent |
|---|---|---|---|
| log_detective | 0.150 | 0.720 | 0.950 |
| cascade_finder | 0.080 | 0.580 | 0.880 |
| full_outage | 0.030 | 0.340 | 0.750 |

## Running Baseline Inference

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="your-token-here"
python inference.py
```
```

---

## ✅ PRE-SUBMISSION CHECKLIST

```
Day 1 (April 5) — Foundation
  ☐ environment.py working (reset/step/state)
  ☐ models.py typed with Pydantic
  ☐ All 3 task files complete
  ☐ All 3 graders returning 0.0–1.0

Day 2 (April 6) — Integration
  ☐ app.py FastAPI server running locally
  ☐ curl localhost:7860/health returns {"status": "ok"}
  ☐ curl -X POST localhost:7860/reset works
  ☐ inference.py runs end-to-end producing 3 scores

Day 3 (April 7) — Deploy
  ☐ docker build . succeeds
  ☐ docker run -p 7860:7860 starts cleanly
  ☐ openenv.yaml complete
  ☐ README complete with all required sections
  ☐ HF Space created and tagged with "openenv"
  ☐ Push code to HF Space repo

Day 4 (April 8) — Final checks
  ☐ HF Space URL returns 200 on /health
  ☐ HF Space responds to /reset
  ☐ inference.py runtime < 20 minutes
  ☐ Graders produce DIFFERENT scores for different action sequences
  ☐ API_BASE_URL, MODEL_NAME, HF_TOKEN env vars set in HF Space secrets
  ☐ Submit before 11:59 PM
```

---

## 📊 EXPECTED SCORES (put these in your README)

| Task | Random Agent | Your Baseline LLM | Strong Agent |
|---|---|---|---|
| log_detective | 0.150 | 0.720 | 0.950 |
| cascade_finder | 0.080 | 0.580 | 0.880 |
| full_outage | 0.030 | 0.340 | 0.750 |

---

## 🧠 KEY DESIGN DECISIONS (explain these in interviews/README)

1. **Dense rewards** — Agent gets credit at EVERY meaningful step, not just episode end. This is what judges look for in "reward shaping."

2. **Order constraints** — In cascade_finder, config must be updated BEFORE restart. This is what makes medium/hard tasks genuinely challenging for LLMs.

3. **3 interacting bugs in full_outage** — Fixing LB first is not just "nice to have" — if you restart payment-service before fixing LB, the service comes back but traffic still can't reach it. This dependency is what makes the hard task genuinely hard.

4. **Score variance guaranteed** — A random agent gets 0.03–0.15. A good agent gets 0.72–0.95. This is a 10x spread which passes Phase 2 variance check.

5. **Nemotron 3 Super will do well on easy, struggle on hard** — By design. This is what makes a good eval environment.
```
