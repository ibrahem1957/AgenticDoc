"""Local-only launcher for the Extraction Lab.

Usage (from any directory, with the lab virtual environment active):
    python -m lab.launch [extra Streamlit options, e.g. --server.port 8502]

Why this exists: Streamlit reads `.streamlit/config.toml` only from the current
working directory, so `lab/.streamlit/config.toml` is ignored when the app is
started from `Project sdaia/`. Started that way, Streamlit binds to all network
interfaces, looks up the machine's external IP through an internet service, and
enables browser usage statistics. The E1 lab must stay local-only and make no
external calls, so the safety options are always passed on the command line.
"""

from __future__ import annotations

import sys
from pathlib import Path

HOME_PAGE = Path(__file__).resolve().parent / "app" / "Home.py"

# Binding to 127.0.0.1 keeps the lab off the network and also stops Streamlit
# from querying an external service for the "External URL" it would print.
SAFE_OPTIONS: tuple[str, ...] = (
    "--server.address",
    "127.0.0.1",
    "--browser.gatherUsageStats",
    "false",
    "--server.maxUploadSize",
    "50",
)
PROTECTED_OPTIONS = frozenset({"--server.address", "--browser.gatherUsageStats"})


def build_argv(extra_options: list[str]) -> list[str]:
    """Return the Streamlit argv. Options must precede the script path."""
    for option in extra_options:
        if option.split("=", 1)[0] in PROTECTED_OPTIONS:
            raise SystemExit(
                f"{option.split('=', 1)[0]} cannot be overridden: the Extraction Lab "
                "is local-only and must not bind to the network or send usage statistics."
            )
    # Safety options come last among the options so they win if repeated.
    return ["streamlit", "run", *extra_options, *SAFE_OPTIONS, str(HOME_PAGE)]


def main(extra_options: list[str] | None = None) -> None:
    from streamlit.web import cli

    sys.argv = build_argv(list(sys.argv[1:] if extra_options is None else extra_options))
    cli.main()


if __name__ == "__main__":
    main()
