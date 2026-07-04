import json


def test_pipeline_writes_nonempty_result_json(sample_result):
    _, out_dir = sample_result
    assert (out_dir / "result.json").stat().st_size > 0


def test_pipeline_writes_nonempty_report_html(sample_result):
    _, out_dir = sample_result
    assert (out_dir / "report.html").stat().st_size > 0


def test_result_json_counts_all_injected_events(sample_result):
    _, out_dir = sample_result
    result = json.loads((out_dir / "result.json").read_text())
    assert result["summary"]["event_counts"] == {
        "speeding": 2,
        "harsh_braking": 1,
        "harsh_accel": 1,
    }


def test_score_reflects_injected_events(sample_result):
    result, _ = sample_result
    assert result.score.value == 78.0


def test_report_shows_the_score(sample_result):
    result, out_dir = sample_result
    assert f"{result.score.value:.0f}/100" in (out_dir / "report.html").read_text()
