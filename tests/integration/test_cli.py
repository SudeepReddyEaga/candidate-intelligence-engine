import json
from pathlib import Path

from candidate_transformer.cli.main import main


def test_cli_writes_output_file(tmp_path: Path) -> None:
    csv_path = tmp_path / "recruiter.csv"
    output_path = tmp_path / "out.json"
    csv_path.write_text(
        "name,email,skills\nAda Lovelace,ada@example.com,python\n", encoding="utf-8"
    )

    exit_code = main(["--csv", str(csv_path), "--output", str(output_path)])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["candidates"][0]["emails"] == ["ada@example.com"]


def test_cli_rejects_empty_inputs() -> None:
    assert main([]) == 2
