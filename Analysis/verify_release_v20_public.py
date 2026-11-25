"""Confirm the stable release and verify both anonymously downloaded assets."""
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "TranslateFiles/reports/release_v20"
REPO = "zfyu222/eschalon-book-i-hanhua"
TAG = "v2.0"
ZIP = "Eschalon.Book.I_.2.0.zip"
HEADERS = {"User-Agent": "StaticHanHua-release-verifier"}


def fetch(url):
    return urlopen(Request(url, headers=HEADERS), timeout=55)


def main():
    package = json.loads((REPORT / "package.json").read_text(encoding="utf-8"))
    release = json.loads(subprocess.check_output(
        ["gh", "release", "view", TAG, "--repo", REPO,
         "--json", "url,tagName,isDraft,isPrerelease,body,assets"], encoding="utf-8"))
    assert release["tagName"] == TAG and not release["isDraft"] and not release["isPrerelease"]
    notes = (REPORT / "release_notes.md").read_text(encoding="utf-8")
    assert release["body"].replace("\r", "").strip() == notes.strip()
    with fetch(f"https://github.com/{REPO}/releases/latest") as response:
        assert response.status == 200 and response.url.endswith("/" + TAG)
    assets = {item["name"]: item for item in release["assets"]}
    assert set(assets) == {ZIP, "title.jpg"}
    asset = assets[ZIP]
    assert asset["state"] == "uploaded" and asset["size"] == package["size"]
    digest = hashlib.sha256()
    size = 0
    with fetch(asset["url"]) as response:
        assert response.status == 200
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    assert size == package["size"] and digest.hexdigest() == package["sha256"]
    with fetch(assets["title.jpg"]["url"]) as response:
        assert response.status == 200 and response.read() == (ROOT / "Dispatch/Artwork/title.jpg").read_bytes()
    evidence = {"status": "passed", "version": TAG, "release": release["url"], "zip_download": asset["url"],
                "sha256": digest.hexdigest(), "size": size, "latest_stable": True,
                "notes_match": True, "cover_verified": True, "archive_http_status": 200,
                "baidu_file_uploaded": False}
    (REPORT / "public_download.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
