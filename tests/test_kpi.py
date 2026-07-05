from b2b_workflow_simulator.kpi import KPIResult


def test_kpi_defaults_are_zero():
    kpi = KPIResult(workflow_name="Test")

    assert kpi.total_cases == 0
    assert kpi.completion_rate == 0.0
    assert kpi.failure_rate == 0.0
    assert kpi.avg_cost_per_case == 0.0
    assert kpi.avg_cycle_time_minutes == 0.0
    assert kpi.bottleneck_nodes() == []


def test_kpi_rates_are_computed_correctly():
    kpi = KPIResult(
        workflow_name="Test",
        total_cases=100,
        completed_cases=80,
        failed_cases=20,
        total_cost=4000.0,
        total_duration_minutes=8000.0,
    )

    assert kpi.completion_rate == 0.8
    assert kpi.failure_rate == 0.2
    assert kpi.avg_cost_per_case == 40.0
    assert kpi.avg_cycle_time_minutes == 80.0


def test_kpi_bottleneck_nodes_ranks_by_total_duration():
    kpi = KPIResult(
        workflow_name="Test",
        node_total_duration_minutes={
            "intake": 100.0,
            "research": 500.0,
            "discovery_call": 900.0,
            "proposal": 300.0,
        },
    )

    top_two = kpi.bottleneck_nodes(top_n=2)

    assert top_two == [("discovery_call", 900.0), ("research", 500.0)]


def test_kpi_bottleneck_nodes_respects_top_n_default():
    kpi = KPIResult(
        workflow_name="Test",
        node_total_duration_minutes={"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0},
    )

    result = kpi.bottleneck_nodes()

    assert len(result) == 3
    assert result[0] == ("d", 4.0)
