# TASK: full_outage
# DIFFICULTY: Hard
# SCENARIO: 3 simultaneous interacting issues causing full production outage
# ISSUES:
#   1. Load balancer misconfigured (P0) - MUST fix first or service restarts don't help
#   2. Payment service memory leak (P1) - fix second
#   3. Stale DNS cache (P1) - fix last (or traffic still won't route correctly)
# KEY CHALLENGE: Issues INTERACT -- fixing in wrong order wastes steps and costs score

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
            "[ERROR] Health check failed: GET /health -> Connection refused",
            "[ERROR] All backend instances marked unhealthy",
            "[INFO]  Config last modified: 03:58 AM (deployment script)",
            "[WARN]  max_connections set to 1 (was 500) -- possible config error"
        ],
        "payment-service": [
            "[ERROR] OOMKilled: memory limit 512Mi exceeded",
            "[ERROR] java.lang.OutOfMemoryError: Java heap space",
            "[INFO]  Heap dump analysis: RetryBuffer holding 2.1M uncleaned objects",
            "[WARN]  Memory leak in RetryBuffer -- fix: restart with -Xmx768m or patch v3.1.2"
        ],
        "dns": [
            "[WARN]  Cached entry for payment.internal points to old IP 10.0.1.45",
            "[INFO]  Actual payment-service IP: 10.0.2.88 (updated after restart)",
            "[INFO]  TTL expired 47 minutes ago -- manual flush required"
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
    # Ground truth -- ORDER MATTERS for scoring
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
