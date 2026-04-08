# TASK: log_detective
# DIFFICULTY: Easy
# SCENARIO: Web server returning 500 errors after a bad deploy
# ROOT CAUSE: api-gateway deployed v2.4.0 which has NullPointerException bug
# SOLUTION: read_logs -> identify api-gateway -> rollback_deploy -> run_healthcheck

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
