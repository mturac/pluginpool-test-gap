"""Regression tests for the test-gap review findings."""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT) not in sys.path:
    sys.path.insert(0, str(SCRIPT))

import gap  # noqa: E402


def test_parse_diff_does_not_treat_content_plus_plus_plus_as_header():
    """A content line beginning with ``+++ `` (e.g. inside a code block) must
    not be misread as a new-file header. Previously this corrupted the line
    counter for the rest of the file."""
    diff = textwrap.dedent("""\
        diff --git a/src/a.py b/src/a.py
        --- a/src/a.py
        +++ b/src/a.py
        @@ -1,0 +1,3 @@
        +x = 1
        ++++ this is a content line, not a header
        +y = 2
    """)
    changed = gap.parse_diff(diff)
    assert "src/a.py" in changed
    # All three "+" lines belong to a.py at lines 1..3
    assert changed["src/a.py"] == [1, 2, 3]


def test_parse_diff_handles_no_prefix_configured(tmp_path):
    """``git -c diff.noprefix=true diff`` emits ``--- src/a.py`` instead of
    ``--- a/src/a.py``. The parser must still extract the filename."""
    diff = textwrap.dedent("""\
        diff --git src/a.py src/a.py
        --- src/a.py
        +++ src/a.py
        @@ -1,0 +1,1 @@
        +new
    """)
    changed = gap.parse_diff(diff)
    assert "src/a.py" in changed
    assert changed["src/a.py"] == [1]


def test_cobertura_merges_duplicate_filenames(tmp_path):
    """Two ``<class>`` entries with the same ``filename=`` must accumulate
    coverage rather than the second overwriting the first."""
    xml = tmp_path / "coverage.xml"
    xml.write_text(textwrap.dedent("""\
        <coverage>
          <packages>
            <package>
              <classes>
                <class filename="src/x.py">
                  <lines>
                    <line number="1" hits="1"/>
                    <line number="2" hits="0"/>
                  </lines>
                </class>
                <class filename="src/x.py">
                  <lines>
                    <line number="3" hits="1"/>
                    <line number="4" hits="0"/>
                  </lines>
                </class>
              </classes>
            </package>
          </packages>
        </coverage>
    """))
    files = gap.parse_cobertura(xml)
    assert "src/x.py" in files
    cov = files["src/x.py"]
    assert cov.covered == {1, 3}
    assert cov.uncovered == {2, 4}


def test_cobertura_respects_sources_prefix(tmp_path):
    """When the report names a relative file (``x.py``) and a ``<source>``
    points to ``src/``, the merged key ``src/x.py`` must also be indexed."""
    xml = tmp_path / "coverage.xml"
    xml.write_text(textwrap.dedent("""\
        <coverage>
          <sources><source>src</source></sources>
          <packages>
            <package>
              <classes>
                <class filename="x.py">
                  <lines>
                    <line number="1" hits="1"/>
                  </lines>
                </class>
              </classes>
            </package>
          </packages>
        </coverage>
    """))
    files = gap.parse_cobertura(xml)
    assert "src/x.py" in files
    assert "x.py" in files  # bare name still indexed


def test_coverage_for_prefers_longest_suffix_match():
    """When two report paths suffix-match a diff path, pick the longer
    overlap to reduce false positives on common basenames."""
    coverage = {
        "utils.py": gap.CoverageFile({1}, set(), 100.0),
        "src/auth/utils.py": gap.CoverageFile({1, 2}, {3}, 66.67),
    }
    # The diff reports ``src/auth/utils.py`` — must prefer the deeper match,
    # not the bare ``utils.py``.
    out = gap.coverage_for("src/auth/utils.py", coverage)
    assert out.covered == {1, 2}


def test_coverage_for_returns_none_pct_when_unknown():
    """Missing files now use ``pct=None`` instead of the -1.0 sentinel."""
    out = gap.coverage_for("nope.py", {})
    assert out.pct is None
