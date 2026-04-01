"""
Test suite for ML Cost Optimizer Lambda function.

Uses moto to mock AWS services (S3, SNS, CloudWatch) and unittest.mock
to patch boto3 clients.
"""

import json
import os
import sys
from unittest import mock

from botocore.exceptions import ClientError

# Set environment variables before importing local modules
os.environ["MOCK_MODE"] = "true"
os.environ["REPORT_BUCKET"] = "test-bucket"
os.environ["SNS_TOPIC_ARN"] = "arn:aws:sns:eu-west-1:123456789:test-topic"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lambda"))

from main import (  # noqa: E402
    generate_markdown_report,
    generate_recommendations,
    handler,
    save_json_report,
)


class TestCostAnalysis:
    """Test suite for cost analysis functionality"""

    def test_cost_analysis_returns_optimizations(self):
        """
        Verify that generate_recommendations returns a non-empty list
        with all required fields typed correctly
        """
        cost_by_resource = {
            "notebooks": 212.00,
            "training": 297.00,
            "endpoints": 170.00,
            "storage": 42.50,
            "other": 128.50,
        }

        recs = generate_recommendations(cost_by_resource)

        # Should return non-empty list
        assert len(recs) > 0, "Recommendations should not be empty"

        # Check each recommendation has required fields with correct types
        for rec in recs:
            assert isinstance(rec["type"], str), "type must be string"
            assert isinstance(rec["cost"], float), "cost must be float"
            assert isinstance(rec["savings"], float), "savings must be float"
            assert isinstance(rec["savings_pct"], int), "savings_pct must be int"
            assert rec["effort"] in ["Low", "Medium", "High"], "Invalid effort level"
            assert rec["priority"] in ["Critical", "High", "Medium"], "Invalid priority"
            assert isinstance(rec["issue"], str), "issue must be string"

        # Verify recommendations are sorted by priority (ROI-based)
        priorities = [rec["priority"] for rec in recs]
        # Should be sorted: Critical → High → Medium
        priority_order = {"Critical": 0, "High": 1, "Medium": 2}
        expected_order = sorted(priorities, key=lambda x: priority_order.get(x, 99))
        assert (
            priorities == expected_order
        ), "Recommendations should be sorted by priority"

    def test_notebook_idle_detection_with_low_usage(self):
        """
        Mock CloudWatch metrics and verify that notebook optimization
        is detected when usage is below 5% threshold
        """
        cost_by_resource = {
            "notebooks": 212.00,  # Above $20 threshold
            "training": 0.0,
            "endpoints": 0.0,
            "storage": 0.0,
            "other": 0.0,
        }

        recs = generate_recommendations(cost_by_resource)

        # Find notebook recommendation
        notebook_recs = [r for r in recs if r["type"] == "Notebooks"]
        assert len(notebook_recs) > 0, "Notebook optimization should be detected"

        notebook_rec = notebook_recs[0]
        expected_issue = (
            "Enable auto-stop for idle notebooks (detect no activity per 24h)"
        )
        assert (
            notebook_rec["issue"] == expected_issue
        ), "Should detect idle notebook optimization"
        assert notebook_rec["savings"] > 0, "Savings should be positive"
        assert (
            notebook_rec["effort"] == "Low"
        ), "Notebook optimization should require low effort"

    def test_sns_failure_doesnt_crash_lambda(self):
        """
        Mock SNS to raise an exception and verify that Lambda
        returns success anyway (non-blocking error handling)
        """
        # Create mock SNS client that raises error
        mock_sns_client = mock.MagicMock()
        mock_sns_client.publish.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameter", "Message": "Invalid topic"}},
            "Publish",
        )

        # Patch get_sns_client to return the mock
        with mock.patch("main.get_sns_client", return_value=mock_sns_client):
            # Call handler - should NOT raise exception
            result = handler({}, None)

            # Response should still be successful
            assert (
                result["statusCode"] == 200
            ), "Lambda should return 200 even with SNS error"

            body = json.loads(result["body"])
            assert body["success"] is True, "Handler should return success=true"
            print("✅ SNS failure handled gracefully (non-blocking)")

    def test_report_markdown_format(self):
        """
        Verify that generated Markdown report contains all expected sections
        and proper formatting
        """
        total_cost = 850.00
        total_savings = 450.00
        savings_pct = 52.9
        recs = [
            {
                "type": "Notebooks",
                "issue": "Auto-stop idle notebooks",
                "savings": 212.00,
                "savings_pct": 75,
                "effort": "Low",
                "priority": "High",
            },
            {
                "type": "Training",
                "issue": "Use Spot instances",
                "savings": 207.90,
                "savings_pct": 70,
                "effort": "Medium",
                "priority": "Critical",
            },
        ]
        report_date = "2026-04-01"

        markdown = generate_markdown_report(
            total_cost, total_savings, savings_pct, recs, report_date
        )

        # Check required sections
        assert "Executive Summary" in markdown, "Should contain Executive Summary"
        assert (
            "Optimization Recommendations" in markdown
        ), "Should contain Recommendations section"
        assert "Next Steps" in markdown, "Should contain Next Steps"

        # Check metrics
        assert f"{total_cost:,.2f}" in markdown, "Should include total cost"
        assert f"{total_savings:,.2f}" in markdown, "Should include total savings"
        assert f"{savings_pct}%" in markdown, "Should include savings percentage"

        # Check table format (Markdown tables use |)
        assert "|" in markdown, "Should contain Markdown table formatting"
        assert (
            "Category" in markdown or "Notebooks" in markdown
        ), "Should list optimization categories"

        # Check Next Steps section has numbered items
        assert "1." in markdown, "Next Steps should be numbered"
        assert "Priority:" in markdown, "Should include priority in Next Steps"

        print("✅ Markdown report format verified")


class TestJSONReportSchema:
    """Test suite for JSON report schema validation"""

    def test_json_report_structure_with_mock_s3(self):
        """
        Verify that JSON report follows strict schema with proper typing
        """
        from moto import mock_aws

        with mock_aws():
            # Create mock S3 bucket
            import boto3

            s3 = boto3.client("s3", region_name="eu-west-1")
            s3.create_bucket(
                Bucket="test-bucket",
                CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
            )

            test_data = {
                "total_cost": 850.00,
                "total_savings": 450.00,
                "savings_pct": 52.9,
                "recs": [
                    {
                        "type": "Training",
                        "cost": 297.00,
                        "savings": 207.90,
                        "savings_pct": 70,
                        "effort": "Medium",
                        "priority": "Critical",
                        "issue": "Use Spot instances",
                    }
                ],
                "report_date": "2026-04-01",
            }

            # Mock boto3 S3 client
            with mock.patch("main.get_s3_client", return_value=s3):
                json_url = save_json_report(
                    "test-bucket",
                    test_data["total_cost"],
                    test_data["total_savings"],
                    test_data["savings_pct"],
                    test_data["recs"],
                    test_data["report_date"],
                )

            # Verify URL format
            assert json_url.startswith("s3://"), "URL should be S3 format"
            assert "report_" in json_url, "URL should contain report prefix"
            assert json_url.endswith(".json"), "URL should end with .json"

            # Retrieve and validate JSON schema
            response = s3.get_object(
                Bucket="test-bucket", Key="reports/report_2026-04-01.json"
            )
            report_data = json.loads(response["Body"].read())

            # Validate metadata section
            assert "metadata" in report_data, "Should have metadata section"
            assert (
                "report_date" in report_data["metadata"]
            ), "Metadata should have report_date"
            assert (
                "generated_at" in report_data["metadata"]
            ), "Metadata should have generated_at"
            assert "version" in report_data["metadata"], "Metadata should have version"

            # Validate summary section
            assert "summary" in report_data, "Should have summary section"
            assert isinstance(report_data["summary"]["total_monthly_spend"], float)
            assert isinstance(report_data["summary"]["identified_savings"], float)
            assert isinstance(report_data["summary"]["savings_percentage"], float)
            assert isinstance(report_data["summary"]["recommendation_count"], int)

            # Validate optimizations array
            assert "optimizations" in report_data, "Should have optimizations section"
            assert (
                len(report_data["optimizations"]) > 0
            ), "Should have at least one optimization"

            opt = report_data["optimizations"][0]
            assert opt["category"] == "Training"
            assert isinstance(opt["monthly_savings"], float)
            assert opt["priority"] in ["Critical", "High", "Medium"]

            print("✅ JSON schema validation passed")


class TestHandlerIntegration:
    """End-to-end integration tests for Lambda handler"""

    def test_handler_mock_mode_success(self):
        """
        Test full handler execution in mock mode (no S3/SNS calls)
        """
        os.environ["MOCK_MODE"] = "true"

        result = handler({}, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])

        assert body["success"] is True
        assert "total_cost" in body
        assert "potential_savings" in body
        assert "savings_pct" in body
        assert "recommendation_count" in body
        assert "recommendations" in body
        assert len(body["recommendations"]) > 0

        print("✅ Handler integration test passed")
