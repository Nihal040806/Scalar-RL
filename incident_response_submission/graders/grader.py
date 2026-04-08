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

    # +0.20 -- Read logs (any service)
    if "read_logs" in action_types:
        score += 0.20
        breakdown["read_logs"] = 0.20

    # +0.30 -- Identified api-gateway as the problem
    if "api-gateway" in services:
        score += 0.30
        breakdown["identified_service"] = 0.30

    # +0.30 -- Applied rollback on api-gateway
    rollback_on_correct = any(
        a.action_type == "rollback_deploy" and a.service == "api-gateway"
        for a in actions_taken
    )
    if rollback_on_correct:
        score += 0.30
        breakdown["applied_fix"] = 0.30

    # +0.10 -- Healthcheck AFTER rollback
    if "rollback_deploy" in action_types and "run_healthcheck" in action_types:
        rollback_idx = action_types.index("rollback_deploy")
        health_idx = action_types.index("run_healthcheck")
        if health_idx > rollback_idx:
            score += 0.10
            breakdown["verified_fix"] = 0.10

    # +0.10 -- Closed incident properly
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

    # +0.25 -- Investigated database (root cause)
    investigated_db = any(
        s == "database" and t in ("check_metrics", "read_logs", "check_config")
        for t, s in action_pairs
    )
    if investigated_db:
        score += 0.25
        breakdown["identified_root_cause"] = 0.25

    # +0.25 -- Config updated BEFORE restart (order constraint)
    config_indices = [i for i, (t, s) in enumerate(action_pairs)
                      if t == "update_config" and s == "database"]
    restart_indices = [i for i, (t, s) in enumerate(action_pairs)
                       if t == "restart_service" and s == "database"]

    if config_indices and restart_indices:
        if min(config_indices) < min(restart_indices):
            score += 0.25
            breakdown["correct_fix_order"] = 0.25

    # +0.25 -- Restarted database
    if ("restart_service", "database") in action_pairs:
        score += 0.25
        breakdown["restarted_db"] = 0.25

    # +0.15 -- Verified recovery
    if "run_healthcheck" in action_types:
        score += 0.15
        breakdown["verified_recovery"] = 0.15

    # +0.10 -- Closed properly
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
        0.15 - Fixed lb-prod (P0 issue -- update max_connections)
        0.15 - Fixed payment-service (rollback to v3.1.2)
        0.15 - Fixed dns (flush_cache)
        0.20 - Fixed in correct priority order (lb -> payment -> dns)
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

    # +0.20 -- Correct priority order (lb before payment before dns)
    if lb_fixed and payment_fixed and dns_fixed:
        lb_idx = next(i for i, (t, s) in enumerate(action_pairs) if t == "update_config" and s == "lb-prod")
        pay_idx = next(i for i, (t, s) in enumerate(action_pairs) if t == "rollback_deploy" and s == "payment-service")
        dns_idx = next(i for i, (t, s) in enumerate(action_pairs) if t == "flush_cache" and s == "dns")
        if lb_idx < pay_idx < dns_idx:
            score += 0.20
            breakdown["correct_priority_order"] = 0.20

    # +0.15 -- Investigated before acting (read logs/metrics before first fix)
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

    # +0.10 -- Healthcheck after all fixes
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

    # +0.10 -- Proper close
    if action_types and action_types[-1] == "close_incident":
        score += 0.10
        breakdown["closed_incident"] = 0.10

    return round(min(score, 1.0), 3), breakdown
