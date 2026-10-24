from pathlib import Path

from streamlit.testing.v1 import AppTest

from vantage.models import Override

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def button(app, label):
    return next(b for b in app.button if b.label == label)


def demo_app():
    app = AppTest.from_file(APP_PATH, default_timeout=20).run()
    button(app, "Explore the demonstration").click().run()
    assert not app.exception
    return app


def test_startup_and_demo_no_api_requests():
    app = AppTest.from_file(APP_PATH, default_timeout=20).run()
    assert not app.exception
    assert app.title[0].value == "Vantage AI"
    button(app, "Explore the demonstration").click().run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["50.0%", "90.0%", "50.0%"]
    assert len(app.slider) == 5


def test_input_changes_hide_stale_results():
    app = demo_app()
    app.text_input(key="product_name").set_value("New Product").run()
    assert not app.exception and len(app.metric) == 0
    assert any("inputs have changed" in w.value for w in app.warning)


def test_manual_edits_persist_through_weights_and_reset():
    app = demo_app()
    app.session_state["overrides"] = {"p0_f2": Override(rating="Yes", note="Human review")}
    app.run()
    assert app.metric[0].value == "75.0%"
    app.slider[0].set_value(10).run()
    assert not app.exception
    assert app.session_state["overrides"]["p0_f2"].note == "Human review"
    assert app.metric[0].value == "70.0%"
    button(app, "Restore original assessments").click().run()
    assert not app.exception and app.session_state["overrides"] == {}
    assert app.slider[0].value == 10


def test_pdf_and_feedback_are_available():
    app = demo_app()
    button(app, "Prepare executive PDF").click().run()
    assert not app.exception
    assert app.session_state["pdf_report"][1].startswith(b"%PDF-")
    button(app, "Prepare anonymous feedback download").click().run()
    assert not app.exception
    assert b'"ease_of_use": 3' in app.session_state["feedback_download"]


def test_manual_mode_with_all_unknowns_starts_and_charts_work():
    app = AppTest.from_file(APP_PATH, default_timeout=20).run()
    app.text_input(key="product_name").set_value("Manual Product")
    app.text_input(key="competitor_0").set_value("Manual Rival")
    app.text_area(key="feature_input").set_value("Alpha\nBravo\nCharlie\nDelta\nEcho")
    button(app, "Start a manual workspace").click().run()
    assert not app.exception
    assert [m.value for m in app.metric] == ["N/A", "N/A"]
    assert app.session_state["active_analysis"].mode == "Manual workspace"
