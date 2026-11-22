import json

import pytest
from playwright.sync_api import expect


@pytest.mark.ui
def test_generate_review_and_export(page, app_url):
    page.goto(app_url)
    page.get_by_label("Acceptance criteria").fill("Reject duplicate synthetic patient identifiers.")
    page.get_by_role("button", name="Generate test cases").click()
    expect(page.get_by_role("status")).to_contain_text("3 draft cases")
    expect(page.get_by_role("status")).to_contain_text("demo-template")
    expect(page.locator("article.case")).to_have_count(3)
    with page.expect_download() as download:
        page.get_by_role("button", name="Export JSON").click()
    data = json.loads(download.value.path().read_text())
    assert data["requires_review"] is True
    assert len(data["suite"]["cases"]) == 3


@pytest.mark.ui
def test_validation_error_is_visible(page, app_url):
    page.goto(app_url)
    page.get_by_label("Acceptance criteria").fill("short")
    page.get_by_role("button", name="Generate test cases").click()
    expect(page.get_by_role("alert")).to_contain_text("10–2000 characters")
    expect(page.get_by_role("button", name="Generate test cases")).to_be_enabled()
