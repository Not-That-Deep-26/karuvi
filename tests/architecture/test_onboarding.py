"""
Unit and Integration Tests for Codebase Onboarding Engine
=========================================================
"""
from pathlib import Path
import pytest

from architecture.analyzer import ArchitectureAnalyzer
from architecture.onboarding import CodebaseOnboardingEngine, OnboardingPlan, OnboardingStep


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent.parent / "fixtures"


def test_onboarding_simple_layered(fixtures_dir):
    repo = fixtures_dir / "simple_layered"
    analyzer = ArchitectureAnalyzer(repo)
    model = analyzer.analyze()

    engine = CodebaseOnboardingEngine(model)
    plan = engine.build_plan()

    assert isinstance(plan, OnboardingPlan)
    assert plan.total_steps == 4
    assert len(plan.steps) == 4
    assert plan.estimated_read_time_minutes > 0

    # Verify steps are ordered by dependency/tier (leaves/models before entrypoint)
    step_modules = [s.target_modules[0] for s in plan.steps]
    
    # Models or storage should appear before main
    api_main_idx = -1
    models_idx = -1
    for idx, s in enumerate(plan.steps):
        if "api/main.py" in s.target_modules:
            api_main_idx = idx
        if "repositories/users.py" in s.target_modules:
            models_idx = idx

    assert models_idx != -1
    assert api_main_idx != -1
    assert models_idx < api_main_idx, "Repositories/storage should be read before API main entrypoint"

    # Verify step properties
    for step in plan.steps:
        assert step.step_number >= 1
        assert len(step.title) > 0
        assert len(step.concept) > 0
        assert len(step.why_now) > 0
        assert len(step.beginner_summary) > 0
        assert len(step.intermediate_summary) > 0
        assert len(step.advanced_summary) > 0

    # Serialization
    plan_dict = plan.to_dict()
    assert plan_dict["total_steps"] == 4
    assert len(plan_dict["steps"]) == 4


def test_onboarding_cycle_handling(fixtures_dir):
    repo = fixtures_dir / "cycles"
    analyzer = ArchitectureAnalyzer(repo)
    model = analyzer.analyze()

    engine = CodebaseOnboardingEngine(model)
    plan = engine.build_plan()

    # In cycles fixture: a.py, b.py, c.py form a 3-module cycle
    cycle_steps = [s for s in plan.steps if s.is_cycle_group]
    assert len(cycle_steps) >= 1
    cycle_step = cycle_steps[0]
    assert len(cycle_step.cycle_modules) >= 2
    assert "cyclic" in cycle_step.concept.lower() or "loop" in cycle_step.concept.lower()
    assert "circular" in cycle_step.why_now.lower() or "loop" in cycle_step.why_now.lower()


def test_onboarding_empty_model():
    from architecture.models import ArchitectureModel
    empty_model = ArchitectureModel(
        repository_root="/tmp/empty",
        modules={},
        components={},
    )
    engine = CodebaseOnboardingEngine(empty_model)
    plan = engine.build_plan()
    assert plan.total_steps == 0
    assert plan.steps == []
