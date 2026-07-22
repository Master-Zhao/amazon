"""CLI entry point for the security audit engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .report_generator import AuditReportGenerator
from .runner import AuditRunner, create_default_registry


def build_audit_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="amazon-ads-audit",
        description="Security audit automation engine for the Amazon Ads Agent PoC",
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        required=True,
        help="Path to the project root directory to audit",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="json,markdown",
        help="Output format(s): json, markdown, or json,markdown (default: json,markdown)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        choices=["security", "compliance", "boundary"],
        help="Filter audit to a specific category (default: all)",
    )
    return parser


def audit_main(argv: list[str] | None = None) -> int:
    parser = build_audit_parser()
    args = parser.parse_args(argv)

    project_path: Path = args.project_path
    if not project_path.is_dir():
        print(f"INPUT_ERROR: Project path does not exist: {project_path}", file=sys.stderr)
        return 2

    try:
        runner = AuditRunner(project_path)
        formats = [f.strip() for f in args.output_format.split(",")]
        generator = runner._report_generator

        if args.category == "security":
            findings = runner.run_security_audit()
            report = generator.generate_report(
                security_findings=findings,
                compliance_findings=(),
                boundary_findings=(),
                project_path=str(project_path),
            )
        elif args.category == "compliance":
            findings = runner.run_compliance_audit()
            report = generator.generate_report(
                security_findings=(),
                compliance_findings=findings,
                boundary_findings=(),
                project_path=str(project_path),
            )
        elif args.category == "boundary":
            findings = runner.run_boundary_audit()
            report = generator.generate_report(
                security_findings=(),
                compliance_findings=(),
                boundary_findings=findings,
                project_path=str(project_path),
            )
        else:
            report = runner.run_full_audit()

        if "json" in formats:
            json_path = project_path / "reports" / f"{report.report_id}.json"
            generator.write_reports(report, json_path=json_path)
            print(f"JSON report written to: {json_path}", file=sys.stderr)

        if "markdown" in formats:
            md_path = project_path / "reports" / f"{report.report_id}.md"
            generator.write_reports(report, markdown_path=md_path)
            print(f"Markdown report written to: {md_path}", file=sys.stderr)

        if report.summary.non_compliant_count > 0:
            print(f"\nAudit completed with {report.summary.non_compliant_count} non-compliant finding(s).", file=sys.stderr)
            return 1

        print("\nAudit completed: all rules compliant.", file=sys.stderr)
        return 0

    except Exception as exc:
        print(f"INTERNAL_ERROR: {exc}", file=sys.stderr)
        return 4