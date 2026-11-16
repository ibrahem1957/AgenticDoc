from __future__ import annotations

import pytest

from lab.launch import HOME_PAGE, SAFE_OPTIONS, build_argv


def test_launcher_forces_localhost_and_disables_usage_stats() -> None:
    argv = build_argv(["--server.port", "8502"])
    assert argv[:2] == ["streamlit", "run"]
    # Options must come before the script path, or Streamlit treats them as script args.
    assert argv[-1] == str(HOME_PAGE)
    options = argv[2:-1]
    assert options[options.index("--server.address") + 1] == "127.0.0.1"
    assert options[options.index("--browser.gatherUsageStats") + 1] == "false"
    assert options[: 2] == ["--server.port", "8502"]
    assert tuple(options[-len(SAFE_OPTIONS):]) == SAFE_OPTIONS
    assert HOME_PAGE.is_file()


def test_readme_launch_instruction_uses_safe_launcher() -> None:
    readme = (HOME_PAGE.parents[1] / "README.md").read_text(encoding="utf-8")
    assert "python -m lab.launch" in readme
    assert "python -m streamlit run" not in readme


@pytest.mark.parametrize(
    "option",
    ["--server.address", "--server.address=0.0.0.0", "--browser.gatherUsageStats=true"],
)
def test_launcher_rejects_overriding_network_and_telemetry_settings(option: str) -> None:
    with pytest.raises(SystemExit, match="local-only"):
        build_argv([option, "0.0.0.0"] if "=" not in option else [option])
