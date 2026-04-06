# TASK: cascade_finder
# DIFFICULTY: Medium
# SCENARIO: Database connection pool exhausted -> 3 microservices failing in cascade
# ROOT CAUSE: database connection pool maxed out (traffic spike + no auto-scaling)
# SOLUTION: check_metrics:database -> update_config:max_connections -> restart_service:database -> run_healthcheck
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
