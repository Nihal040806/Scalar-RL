"""
Script to generate synthetic incident scenarios.
Run this to create additional scenario JSON files in data/scenarios/
"""

import json
import os
import random

SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "scenarios")
os.makedirs(SCENARIOS_DIR, exist_ok=True)


def generate_easy_scenario(scenario_id: int) -> dict:
    """Generate a variation of the easy (log_detective) scenario."""
    services = ["api-gateway", "web-frontend", "auth-service", "notification-service"]
    root_service = random.choice(services)
    old_version = f"v{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,9)}"
    new_version = f"v{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,9)}"
    error_rate = random.randint(20, 80)

    return {
        "scenario_id": f"easy_{scenario_id:03d}",
        "task_name": "log_detective",
        "difficulty": "easy",
        "description": f"{root_service} returning 500 errors after deploy {new_version}",
        "initial_alerts": [
            f"CRITICAL: {root_service} 500 error rate at {error_rate}% (threshold: 1%)",
            f"WARNING: Downstream failures increasing"
        ],
        "initial_system_status": {
            root_service: "degraded",
            "database": "healthy",
            "cache": "healthy"
        },
        "root_cause": "bad_deploy",
        "root_cause_service": root_service,
        "correct_fix_action": "rollback_deploy",
        "correct_rollback_version": old_version,
        "max_steps": 15
    }


def generate_medium_scenario(scenario_id: int) -> dict:
    """Generate a variation of the medium (cascade_finder) scenario."""
    max_conns = random.choice([50, 100, 150])
    downstream = random.sample(["user-service", "order-service", "payment-service", "auth-service"], 2)

    return {
        "scenario_id": f"medium_{scenario_id:03d}",
        "task_name": "cascade_finder",
        "difficulty": "medium",
        "description": f"Database connection pool exhausted at {max_conns}/{max_conns}, cascading to {', '.join(downstream)}",
        "initial_alerts": [
            f"CRITICAL: {downstream[0]} - Cannot connect to database (timeout)",
            f"CRITICAL: {downstream[1]} - Cannot connect to database (timeout)",
            f"WARNING: database - Connection pool utilization at 100%"
        ],
        "initial_system_status": {
            downstream[0]: "down",
            downstream[1]: "down",
            "database": "degraded",
            "cache": "healthy"
        },
        "root_cause": "connection_pool_exhausted",
        "root_cause_service": "database",
        "correct_config_key": "max_connections",
        "correct_config_value": max_conns * 3,
        "max_steps": 20
    }


def generate_hard_scenario(scenario_id: int) -> dict:
    """Generate a variation of the hard (full_outage) scenario."""
    lb_max_conns = random.choice([1, 2, 5])
    memory_pct = random.randint(90, 99)
    payment_version = f"v3.1.{random.randint(0, 5)}"
    stable_version = f"v3.1.{random.randint(6, 9)}"

    return {
        "scenario_id": f"hard_{scenario_id:03d}",
        "task_name": "full_outage",
        "difficulty": "hard",
        "description": f"Full outage: LB misconfigured (max_conn={lb_max_conns}), payment OOM ({memory_pct}%), stale DNS",
        "initial_alerts": [
            f"P0 CRITICAL: lb-prod - Health checks failing, max_connections={lb_max_conns}",
            f"P1 CRITICAL: payment-service - Memory at {memory_pct}%, OOMKilled",
            f"P1 WARNING: dns - Stale cache entries"
        ],
        "initial_system_status": {
            "lb-prod": "down",
            "payment-service": "down",
            "dns": "degraded",
            "api-gateway": "degraded",
            "database": "healthy"
        },
        "root_causes": {
            "lb-prod": {"type": "misconfigured_max_connections", "severity": "P0"},
            "payment-service": {"type": "memory_leak", "severity": "P1"},
            "dns": {"type": "stale_cache", "severity": "P1"}
        },
        "correct_fix_order": ["lb-prod", "payment-service", "dns"],
        "max_steps": 30
    }


def main():
    all_scenarios = []

    # Generate easy scenarios
    for i in range(1, 3):
        scenario = generate_easy_scenario(i)
        filepath = os.path.join(SCENARIOS_DIR, f"easy_{i:03d}.json")
        with open(filepath, "w") as f:
            json.dump(scenario, f, indent=2)
        all_scenarios.append(filepath)
        print(f"Generated: {filepath}")

    # Generate medium scenarios
    for i in range(1, 3):
        scenario = generate_medium_scenario(i)
        filepath = os.path.join(SCENARIOS_DIR, f"medium_{i:03d}.json")
        with open(filepath, "w") as f:
            json.dump(scenario, f, indent=2)
        all_scenarios.append(filepath)
        print(f"Generated: {filepath}")

    # Generate hard scenarios
    for i in range(1, 3):
        scenario = generate_hard_scenario(i)
        filepath = os.path.join(SCENARIOS_DIR, f"hard_{i:03d}.json")
        with open(filepath, "w") as f:
            json.dump(scenario, f, indent=2)
        all_scenarios.append(filepath)
        print(f"Generated: {filepath}")

    print(f"\nGenerated {len(all_scenarios)} scenario files in {SCENARIOS_DIR}")


if __name__ == "__main__":
    main()
