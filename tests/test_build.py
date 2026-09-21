import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("build_mini", Path(__file__).parents[1] / "scripts/build_mini.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("target,suffix", [("wechat", ".wxml"), ("qq", ".qml")])
def test_native_source_packages_have_all_registered_pages(tmp_path, target, suffix):
    destination = module.build(target, "http://127.0.0.1:8000", "", tmp_path)
    config = json.loads((destination / "app.json").read_text())
    assert len(config["pages"]) == 8
    for page in config["pages"]:
        assert (destination / (page + suffix)).exists()
        assert (destination / (page + ".js")).exists()
        assert (destination / (page + ".json")).exists()
    if target == "qq":
        assert "wx:" not in (destination / "pages/home/index.qml").read_text()
        assert (destination / "app.qss").exists()
        assert not (destination / "app.wxss").exists()


def test_production_build_requires_https_and_appid(tmp_path):
    with pytest.raises(ValueError):
        module.build("wechat", "http://localhost", "app", tmp_path, production=True)
    with pytest.raises(ValueError):
        module.build("wechat", "https://example.test", "", tmp_path, production=True)


def test_backup_keeps_committed_records_and_never_overwrites(tmp_path):
    import sqlite3
    backup_spec=importlib.util.spec_from_file_location('backup',Path(__file__).parents[1]/'scripts/backup.py')
    backup_module=importlib.util.module_from_spec(backup_spec);backup_spec.loader.exec_module(backup_module)
    source,destination=tmp_path/'source.sqlite',tmp_path/'copy.sqlite'
    with sqlite3.connect(source) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE sample(value TEXT)')
        db.execute("INSERT INTO sample VALUES('saved')")
    backup_module.backup(source,destination)
    with sqlite3.connect(destination) as db:assert db.execute('SELECT value FROM sample').fetchone()[0]=='saved'
    with pytest.raises(ValueError):backup_module.backup(source,destination)
