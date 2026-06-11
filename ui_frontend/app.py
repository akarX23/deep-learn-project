"""Streamlit application shell for the tutoring frontend."""

from __future__ import annotations

import streamlit as st

from ui_frontend.config import UIConfig


def _render_status_panel(config: UIConfig) -> None:
    st.sidebar.subheader("Status")
    st.sidebar.write("Connection: disconnected")
    st.sidebar.write(f"WebSocket URL: {config.websocket_url}")
    st.sidebar.write(
        f"Simulator enabled by env: {'yes' if config.simulator_enabled else 'no'}"
    )


def main() -> None:
    st.set_page_config(page_title="AI Tutor", page_icon="Tutor", layout="wide")
    st.title("Multi-Agent AI Tutor")

    try:
        config = UIConfig.from_env()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    _render_status_panel(config)

    chat_tab, quiz_tab, evaluation_tab = st.tabs(["Chat", "Quiz", "Evaluation"])

    with chat_tab:
        st.subheader("Chat")
        st.info("Teaching stream will appear here.")

    with quiz_tab:
        st.subheader("Quiz")
        st.info("Quiz events will appear here.")

    with evaluation_tab:
        st.subheader("Evaluation")
        st.info("Evaluation results will appear here.")


if __name__ == "__main__":
    main()
