import os
import json
import pytest
from backend.app.database.db import db_manager
from backend.app.guardrails.validator import SQLGuardrail
from backend.app.agents.stats_engine import stats_engine
from backend.app.agents.state import AgentState
from backend.app.agents.graph import agent_workflow

def test_database_connection_and_seeding():
    df, elapsed, err = db_manager.execute_query("SELECT COUNT(*) AS cnt FROM users")
    assert err is None
    assert df is not None
    assert df["cnt"].iloc[0] > 0

def test_statistical_engine_z_test_ground_truth():
    res = stats_engine.calculate_ab_test(100, 1000, 150, 1000)
    assert res["relative_lift_pct"] == 50.0
    assert res["statistically_significant"] is True
    assert res["p_value"] < 0.01

def test_srm_detection():
    srm = stats_engine.check_sample_ratio_mismatch(3500, 1500)
    assert srm["srm_detected"] is True
    assert srm["p_value"] < 0.0001

def test_sql_guardrail_blocks_destructive_commands():
    malicious = "DROP TABLE users;"
    valid, err = SQLGuardrail.validate_sql(malicious)
    assert valid is False
    assert "forbidden mutation keyword" in err

def test_benchmark_golden_queries():
    cases_path = os.path.join(os.path.dirname(__file__), "benchmark_cases.json")
    with open(cases_path, "r", encoding="utf-8-sig") as f:
        benchmarks = json.load(f)
        
    for tc in benchmarks:
        state = AgentState(user_query=tc["question"], provider="mock")
        res = agent_workflow.run(state)
        
        assert res.intent == tc["expected_intent"], f"Failed intent on {tc['id']}"
        assert res.generated_sql is not None
        assert res.sql_error is None, f"SQL error on {tc['id']}: {res.sql_error}"
        assert len(res.query_result_data) > 0
        assert res.executive_memo is not None
