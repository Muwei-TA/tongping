"""Generate native source packages, not a substitute for host compiler validation."""
import argparse
import json
from pathlib import Path
import shutil
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def build(target, api_base, appid, output, production=False):
    parsed = urlsplit(api_base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
        raise ValueError("api-base must be a plain HTTP(S) service origin")
    if parsed.path not in ("", "/"):
        raise ValueError("api-base must not contain a path")
    if production and (not appid or parsed.scheme != "https"):
        raise ValueError("Production builds require an AppID and HTTPS API origin")
    destination = output / target
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(ROOT / "mini", destination)
    suffixes = {".wxml": ".qml", ".wxss": ".qss"} if target == "qq" else {}
    for file in list(destination.rglob("*")):
        if file.is_file() and file.suffix in suffixes:
            text = file.read_text().replace("wx:", "qq:")
            new_file = file.with_suffix(suffixes[file.suffix])
            new_file.write_text(text)
            file.unlink()
    (destination / "lib" / "config.js").write_text("module.exports = " + json.dumps({"apiBase": api_base.rstrip("/"), "provider": target}, ensure_ascii=False) + ";\n")
    app = json.loads((destination / "app.json").read_text())
    if target == "qq":
        app.pop("style", None)
    (destination / "app.json").write_text(json.dumps(app, ensure_ascii=False, indent=2) + "\n")
    for page in app["pages"]:
        (destination / (page + ".json")).write_text('{}\n')
        for suffix in (".js", ".qml" if target == "qq" else ".wxml"):
            if not (destination / (page + suffix)).is_file():
                raise ValueError(f"Missing page source: {page}{suffix}")
    project = {"appid": appid, "projectname": "tongping-" + target, "miniprogramRoot": "./",
               "setting": {"es6": True, "minified": True, "urlCheck": production}}
    (destination / "project.config.json").write_text(json.dumps(project, indent=2) + "\n")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["all", "wechat", "qq"], default="all")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--wechat-appid", default="")
    parser.add_argument("--qq-appid", default="")
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    targets = ("wechat", "qq") if args.target == "all" else (args.target,)
    for target in targets:
        path = build(target, args.api_base, getattr(args, target + "_appid"), ROOT / "build", args.production)
        print(f"Generated {path}; import into the matching developer tools for host compilation.")


if __name__ == "__main__":
    main()
