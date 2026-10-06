from pathlib import Path

from mender.eval import CaseResult, _evidence_manifests, aggregate, load_faults

REPO = Path(__file__).resolve().parents[1]


def test_load_faults_finds_full_catalogue() -> None:
    faults = load_faults(REPO / "demo")
    assert len(faults) == 23
    assert len({fault.id for fault in faults}) == 23
    for fault in faults:
        assert fault.files, fault.id
        assert fault.expected_labels, fault.id
        assert all(path.startswith("demo/") for path in fault.files), fault.id
        assert fault.signal in {"cluster", "file"}


def _case(
    fault_id: str,
    *,
    status: str = "pr-prepared",
    correct: bool = True,
    passed: bool = True,
    time_ms: float | None = 1000.0,
    cost: float | None = 0.01,
) -> CaseResult:
    return CaseResult(
        fault_id=fault_id,
        category="config",
        status=status,
        root_cause_correct=correct,
        verify_passed=passed,
        time_to_pr_ready_ms=time_ms,
        cost_usd_by_tier={"nano": cost, "ultra": cost, "tavily": None},
        tokens_by_tier={"nano": 100, "ultra": 200, "tavily": 0},
        calls_by_tier={"nano": 1, "ultra": 2, "tavily": 3},
    )


def test_aggregate_scores_honestly() -> None:
    cases = [
        _case("a"),
        _case("b", status="verify-failed", correct=False, passed=False, time_ms=None),
        _case("c", status="error", correct=False, passed=False, time_ms=None),
    ]
    report = aggregate(
        cases,
        fault_count=3,
        started_at="t0",
        finished_at="t1",
        pr_mode="prepare",
        settle_s=20,
        sandbox_image="img",
    )
    summary = report.summary
    assert summary.cases_run == 3
    assert summary.root_cause_correct == 1
    assert summary.root_cause_accuracy == 1 / 3
    assert summary.fix_pass_rate == 1 / 3
    assert summary.time_to_pr_ready_ms_median == 1000.0
    assert summary.time_to_pr_ready_n == 1
    # Tavily has no published per-search price; model tiers sum when known.
    assert summary.cost_usd_by_tier["tavily"] is None
    assert summary.cost_usd_by_tier["ultra"] == 0.03
    assert summary.tokens_by_tier["ultra"] == 600
    assert summary.calls_by_tier["tavily"] == 9
    assert [f["fault_id"] for f in summary.failures] == ["b", "c"]
    assert report.model_dump()["schema_version"] == "mender-eval-v1"


def test_tier_cost_is_none_when_any_call_lacks_a_price() -> None:
    cases = [_case("a"), _case("b", cost=None)]
    report = aggregate(
        cases,
        fault_count=2,
        started_at="t0",
        finished_at="t1",
        pr_mode="prepare",
        settle_s=20,
        sandbox_image="img",
    )
    assert report.summary.cost_usd_by_tier["ultra"] is None


def test_case_without_calls_does_not_poison_tier_cost() -> None:
    """A case that never called a tier (e.g. inject failure) must not make the
    tier's cost unknown — only an unpriced CALL does."""
    no_calls = CaseResult(
        fault_id="inject-failed",
        category="scheduling",
        status="inject-failed",
        root_cause_correct=False,
        verify_passed=False,
        time_to_pr_ready_ms=None,
    )
    report = aggregate(
        [_case("a"), no_calls, _case("b")],
        fault_count=3,
        started_at="t0",
        finished_at="t1",
        pr_mode="prepare",
        settle_s=20,
        sandbox_image="img",
    )
    summary = report.summary
    assert summary.cost_usd_by_tier["nano"] == 0.02
    assert summary.cost_usd_by_tier["ultra"] == 0.02
    assert summary.cost_usd_by_tier["tavily"] is None


def test_aggregate_empty_run_is_zero_not_crash() -> None:
    report = aggregate(
        [],
        fault_count=23,
        started_at="t0",
        finished_at="t1",
        pr_mode="prepare",
        settle_s=20,
        sandbox_image="img",
    )
    assert report.summary.root_cause_accuracy == 0.0
    assert report.summary.time_to_pr_ready_ms_median is None


def test_evidence_manifests_includes_source_and_migrations(tmp_path: Path) -> None:
    demo = tmp_path / "demo"
    (demo / "manifests").mkdir(parents=True)
    (demo / "app").mkdir()
    (demo / "migrations").mkdir()
    (demo / "manifests" / "deploy.yaml").write_text("kind: Deployment")
    (demo / "app" / "service.py").write_text("x = 1")
    (demo / "app" / "check.py").write_text("y = 2")
    (demo / "migrations" / "001_init.sql").write_text("CREATE TABLE t ();")

    files = _evidence_manifests(tmp_path)
    assert set(files) == {
        "demo/manifests/deploy.yaml",
        "demo/app/service.py",
        "demo/app/check.py",
        "demo/migrations/001_init.sql",
    }
