"""
Basic sanity tests for the Incident Response OpenEnv environment.
Run with: pytest tests/test_environment.py -v
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environment import IncidentResponseEnv
from models import Action


class TestEasyTask:
    """Tests for log_detective (easy) task"""

    def setup_method(self):
        self.env = IncidentResponseEnv("log_detective")
        self.obs = self.env.reset()

    def test_reset_returns_observation(self):
        assert self.obs.alerts is not None
        assert len(self.obs.alerts) > 0
        assert self.obs.steps_taken == 0
        assert self.obs.max_steps == 15

    def test_initial_system_status(self):
        assert self.obs.system_status["api-gateway"] == "degraded"
        assert self.obs.system_status["database"] == "healthy"

    def test_read_logs_returns_data(self):
        action = Action(action_type="read_logs", service="api-gateway")
        obs, reward, done, info = self.env.step(action)
        assert "NullPointerException" in obs.last_action_result
        assert not done

    def test_perfect_run_scores_high(self):
        """Test the optimal action sequence scores ~1.0"""
        actions = [
            Action(action_type="read_logs", service="api-gateway"),
            Action(action_type="rollback_deploy", service="api-gateway", version="v2.3.1"),
            Action(action_type="run_healthcheck"),
            Action(action_type="close_incident"),
        ]
        for action in actions:
            obs, reward, done, info = self.env.step(action)

        assert info["cumulative_score"] == 1.0
        assert done

    def test_max_steps_ends_episode(self):
        """Verify episode ends when max steps reached"""
        action = Action(action_type="check_metrics", service="database")
        for _ in range(15):
            obs, reward, done, info = self.env.step(action)
        assert done

    def test_rollback_fixes_service(self):
        action = Action(action_type="rollback_deploy", service="api-gateway", version="v2.3.1")
        obs, reward, done, info = self.env.step(action)
        assert obs.system_status["api-gateway"] == "healthy"


class TestMediumTask:
    """Tests for cascade_finder (medium) task"""

    def setup_method(self):
        self.env = IncidentResponseEnv("cascade_finder")
        self.obs = self.env.reset()

    def test_reset_returns_observation(self):
        assert self.obs.steps_taken == 0
        assert self.obs.max_steps == 20

    def test_initial_status_shows_cascade(self):
        assert self.obs.system_status["database"] == "degraded"
        assert self.obs.system_status["user-service"] == "down"
        assert self.obs.system_status["order-service"] == "down"

    def test_perfect_run(self):
        actions = [
            Action(action_type="check_metrics", service="database"),
            Action(action_type="update_config", service="database", key="max_connections", value=300),
            Action(action_type="restart_service", service="database"),
            Action(action_type="run_healthcheck"),
            Action(action_type="close_incident"),
        ]
        for action in actions:
            obs, reward, done, info = self.env.step(action)

        assert info["cumulative_score"] == 1.0
        assert done

    def test_restart_recovers_cascade(self):
        action = Action(action_type="restart_service", service="database")
        obs, reward, done, info = self.env.step(action)
        assert obs.system_status["database"] == "healthy"
        assert obs.system_status["user-service"] == "healthy"
        assert obs.system_status["order-service"] == "healthy"


class TestHardTask:
    """Tests for full_outage (hard) task"""

    def setup_method(self):
        self.env = IncidentResponseEnv("full_outage")
        self.obs = self.env.reset()

    def test_reset_returns_observation(self):
        assert self.obs.steps_taken == 0
        assert self.obs.max_steps == 30

    def test_all_three_issues_present(self):
        assert self.obs.system_status["lb-prod"] == "down"
        assert self.obs.system_status["payment-service"] == "down"
        assert self.obs.system_status["dns"] == "degraded"

    def test_perfect_run(self):
        actions = [
            Action(action_type="read_logs", service="lb-prod"),
            Action(action_type="read_logs", service="payment-service"),
            Action(action_type="read_logs", service="dns"),
            Action(action_type="update_config", service="lb-prod", key="max_connections", value=500),
            Action(action_type="rollback_deploy", service="payment-service", version="v3.1.2"),
            Action(action_type="flush_cache", service="dns"),
            Action(action_type="run_healthcheck"),
            Action(action_type="close_incident"),
        ]
        for action in actions:
            obs, reward, done, info = self.env.step(action)

        assert info["cumulative_score"] == 1.0
        assert done

    def test_wrong_order_loses_points(self):
        """Fixing in wrong order should score lower than perfect"""
        actions = [
            Action(action_type="read_logs", service="lb-prod"),
            Action(action_type="flush_cache", service="dns"),  # Wrong order: dns before lb
            Action(action_type="rollback_deploy", service="payment-service", version="v3.1.2"),
            Action(action_type="update_config", service="lb-prod", key="max_connections", value=500),
            Action(action_type="run_healthcheck"),
            Action(action_type="close_incident"),
        ]
        for action in actions:
            obs, reward, done, info = self.env.step(action)

        # Should not get the priority order bonus (0.20)
        assert info["cumulative_score"] < 1.0
        assert "correct_priority_order" not in info["breakdown"]


class TestEnvironmentEdgeCases:
    """Edge case tests"""

    def test_invalid_task_raises(self):
        with pytest.raises(AssertionError):
            IncidentResponseEnv("nonexistent_task")

    def test_step_after_done_raises(self):
        env = IncidentResponseEnv("log_detective")
        env.reset()
        env.step(Action(action_type="close_incident"))
        with pytest.raises(ValueError):
            env.step(Action(action_type="read_logs", service="api-gateway"))

    def test_state_returns_info(self):
        env = IncidentResponseEnv("log_detective")
        env.reset()
        state = env.state()
        assert state["task_name"] == "log_detective"
        assert state["step_count"] == 0
        assert state["done"] is False

    def test_unknown_service_logs(self):
        env = IncidentResponseEnv("log_detective")
        env.reset()
        obs, reward, done, info = env.step(
            Action(action_type="read_logs", service="nonexistent-service")
        )
        assert "No logs found" in obs.last_action_result

    def test_reward_always_between_0_and_1(self):
        env = IncidentResponseEnv("log_detective")
        env.reset()
        for _ in range(15):
            obs, reward, done, info = env.step(
                Action(action_type="read_logs", service="api-gateway")
            )
            assert 0.0 <= reward.score <= 1.0
            assert 0.0 <= reward.cumulative_score <= 1.0
            if done:
                break


class TestFastAPI:
    """Test the FastAPI endpoints"""

    def test_app_imports(self):
        from app import app
        assert app.title == "Incident Response OpenEnv"

    def test_endpoints_exist(self):
        from app import app
        routes = [r.path for r in app.routes]
        assert "/health" in routes
        assert "/reset" in routes
        assert "/step" in routes
        assert "/state" in routes
        assert "/tasks" in routes
