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
  "available_actions": ["read_logs", "check_metrics", "..."]
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

## Key Design Decisions

1. **Dense rewards** — Agent gets credit at EVERY meaningful step, not just episode end.
2. **Order constraints** — In cascade_finder, config must be updated BEFORE restart.
3. **3 interacting bugs in full_outage** — Fixing in wrong order wastes steps and costs score.
4. **Score variance guaranteed** — A random agent gets 0.03–0.15. A good agent gets 0.72–0.95. This is a 10x spread.

## Running Baseline Inference

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="your-token-here"
python inference.py
```
