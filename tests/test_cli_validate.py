from pathlib import Path

from typer.testing import CliRunner

from w2_agent.cli import app


runner = CliRunner()


def test_validate_command_with_text_file(tmp_path: Path) -> None:
    sample = tmp_path / "sample_w2.txt"
    sample.write_text(
        "\n".join(
            [
                "Form W-2",
                "1 Wages, tips, other compensation 10,000.00",
                "2 Federal income tax withheld 0.00",
                "3 Social security wages 10,000.00",
                "5 Medicare wages and tips 10,000.00",
                "12a D 500.00",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["validate", "--w2-file", str(sample), "--show-parsed"],
    )

    assert result.exit_code == 0
    assert "Validation Summary" in result.stdout
    assert "box1_wages: 10000.0" in result.stdout
    assert "ZERO_WITHHOLDING" in result.stdout


def test_validate_command_missing_file() -> None:
    result = runner.invoke(app, ["validate", "--w2-file", "/tmp/does-not-exist.pdf"])
    assert result.exit_code == 1
    assert "W-2 file not found" in result.stdout
