from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_starts_without_errors() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)
    assert not app.exception

