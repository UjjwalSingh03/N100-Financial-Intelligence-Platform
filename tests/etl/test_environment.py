from pathlib import Path


def test_project_directories_exist_or_can_be_created() -> None:
    root = Path(__file__).resolve().parents[2]
    for relative_path in (
        "data/raw",
        "data/processed",
        "db",
        "notebooks",
        "output",
        "src/etl",
        "tests/etl",
    ):
        path = root / relative_path
        path.mkdir(parents=True, exist_ok=True)
        assert path.is_dir()


def test_environment_template_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / ".env.example").is_file()


def test_requirements_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "requirements.txt").is_file()
