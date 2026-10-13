
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
APP_TIMEOUT = 10


def test_app_loads_successfully():
    """Check that the Streamlit app loads without errors."""
    app = AppTest.from_file(str(APP_PATH)).run(timeout=APP_TIMEOUT)

    assert not app.exception, (
        f"The app encountered an error: {app.exception}"
    )

    assert any(
        "Multi-Agent AI Test Assistant" in title.value
        for title in app.title
    ), "The expected app title was not found."


def test_empty_requirements_show_warning():
    """Check that empty requirements display a warning."""
    app = AppTest.from_file(str(APP_PATH)).run(timeout=APP_TIMEOUT)

    generate_buttons = [
        button
        for button in app.button
        if "generate" in button.label.lower()
    ]

    assert generate_buttons, (
        "Could not find a button with 'Generate' in its label."
    )

    generate_buttons[0].click().run(timeout=APP_TIMEOUT)

    assert any(
        "Please enter at least one requirement." in warning.value
        for warning in app.warning
    ), "The expected empty-requirements warning was not displayed."
