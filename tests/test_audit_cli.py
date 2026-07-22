"""Unit tests for the audit CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from amazon_ads_agent.security_audit.cli import audit_main, build_audit_parser


class TestBuildAuditParser:
    def test_parse_project_path(self):
        parser = build_audit_parser()
        args = parser.parse_args(["--project-path", "/tmp/test"])
        assert args.project_path == Path("/tmp/test")

    def test_parse_output_format(self):
        parser = build_audit_parser()
        args = parser.parse_args(["--project-path", "/tmp/test", "--output-format", "json"])
        assert args.output_format == "json"

    def test_parse_category(self):
        parser = build_audit_parser()
        args = parser.parse_args(["--project-path", "/tmp/test", "--category", "security"])
        assert args.category == "security"


class TestAuditMain:
    def test_nonexistent_path_returns_2(self):
        result = audit_main(["--project-path", "/nonexistent/path/xyz"])
        assert result == 2

    def test_valid_project_returns_0_or_1(self, tmp_path):
        src_dir = tmp_path / "src" / "amazon_ads_agent"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("", encoding="utf-8")
        result = audit_main(["--project-path", str(tmp_path), "--output-format", "json"])
        assert result in (0, 1)

    def test_category_security(self, tmp_path):
        src_dir = tmp_path / "src" / "amazon_ads_agent"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("", encoding="utf-8")
        result = audit_main(["--project-path", str(tmp_path), "--category", "security", "--output-format", "json"])
        assert result in (0, 1)

    def test_json_output(self, tmp_path):
        src_dir = tmp_path / "src" / "amazon_ads_agent"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("", encoding="utf-8")
        audit_main(["--project-path", str(tmp_path), "--output-format", "json"])
        reports = list((tmp_path / "reports").glob("*.json"))
        assert len(reports) >= 1