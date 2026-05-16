import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import gap


FIXTURES = Path(__file__).parent / "fixtures"


def test_diff_parser_collects_added_lines():
    diff = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1,0 +2,2 @@
+first
+second
@@ -7 +9,0 @@
-old
"""
    assert gap.parse_diff(diff) == {"src/app.py": [2, 3]}


def test_lcov_parse():
    parsed = gap.parse_lcov(FIXTURES / "lcov.info")
    assert parsed["src/app.py"].covered == {1, 5}
    assert parsed["src/app.py"].uncovered == {2}


def test_cobertura_parse():
    parsed = gap.parse_cobertura(FIXTURES / "coverage.xml")
    assert parsed["src/app.py"].uncovered == {2}
    assert parsed["src/app.py"].pct == 66.67


def test_coverage_json_parse():
    parsed = gap.parse_coverage_json(FIXTURES / "coverage.json")
    assert parsed["src/app.py"].covered == {1, 3}
    assert parsed["src/app.py"].uncovered == {2, 4}
    assert parsed["src/app.py"].pct == 50.0


def test_json_shape_for_uncovered_changed_lines():
    coverage = gap.parse_coverage_json(FIXTURES / "coverage.json")
    result = gap.build_result({"src/app.py": [1, 2, 4]}, coverage)
    assert json.loads(json.dumps(result)) == {
        "files": [{
            "path": "src/app.py",
            "changed_lines": [1, 2, 4],
            "uncovered_lines": [2, 4],
            "coverage_pct": 50.0,
        }],
        "coverage_loaded": True,
    }


def test_markdown_rendering_sorts_by_uncovered_count():
    result = {
        "files": [
            {"path": "b.py", "changed_lines": [1], "uncovered_lines": [], "coverage_pct": 100.0},
            {"path": "a.py", "changed_lines": [1, 2], "uncovered_lines": [1, 2], "coverage_pct": 0.0},
        ]
    }
    rendered = gap.markdown(result)
    assert rendered.splitlines()[2].startswith("| a.py ")
    assert "1,2" in rendered


def test_empty_diff():
    result = gap.build_result(gap.parse_diff(""), {})
    assert result == {"files": [], "coverage_loaded": False}
    assert gap.markdown(result) == "No changed lines found."


def test_missing_explicit_report_is_not_silent_pass(tmp_path, monkeypatch):
    """If --report points at a nonexistent file, the CLI must NOT report 100% covered."""
    monkeypatch.chdir(tmp_path)
    rc = gap.main(["--report", str(tmp_path / "does-not-exist.xml")])
    assert rc == 2


def test_no_report_detected_marks_lines_as_gaps():
    """With no coverage at all, every changed line is treated as a gap."""
    result = gap.build_result({"src/app.py": [1, 2, 4]}, {})
    files = result["files"]
    assert files[0]["uncovered_lines"] == [1, 2, 4]
    assert files[0]["coverage_pct"] is None
    assert result["coverage_loaded"] is False
