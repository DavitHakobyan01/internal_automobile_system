import sys
import types

registry_stub = types.ModuleType("registry")
registry_stub.SCRAPERS = []
sys.modules["registry"] = registry_stub

from app import app  # noqa: E402


def test_scrape_monitor_requires_login():
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/scrape-monitor")

    assert response.status_code == 302
    assert "/" in response.headers.get("Location", "")


def test_scrape_monitor_renders_shell_when_logged_in():
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as session:
        session["role"] = "admin"
        session["username"] = "tester"

    response = client.get("/scrape-monitor")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Scrape Monitor" in html
    assert "monitor-table-body" in html
    assert "monitor-running" in html