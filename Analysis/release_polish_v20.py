"""Stage, verify, package and deploy the v2.0 single-entry localization."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Release/v20_build"
OLD_FILES = ROOT / "Dispatch/Files"
BASE = ROOT / "ImagePatch/backup/gfx.pak"
ORIGINAL, V19 = json.loads((BUILD / "build.json").read_text(encoding="utf-8"))["delta"]["supported_base_hashes"]

WORKSPACE = ROOT.parents[1]
RELEASE_TOOL = WORKSPACE / ".agents/skills/game-release-patch/scripts"
sys.path.insert(0, str(RELEASE_TOOL))
from create_release_patch import make_guide, next_version, previous_changelog

DISPATCH = ROOT / "Dispatch"
ARCHIVE_OLD = DISPATCH / "StagingArchive/v19_before_v20"
STAGE = BUILD / "stage"
REPORT = ROOT / "TranslateFiles/reports/release_v20"
GAME = "Eschalon Book I"
VERSION = "2.0"
TITLE = "[子非鱼Ai汉化]《埃斯卡隆：卷一》/《Eschalon: Book I》"
ENTRY = "埃斯卡隆：卷一_中文版.exe"
RUNTIME = "汉化工具/runtime/EschalonBook_Chinese_Launcher.exe"
DELTA = "汉化文件/gfx.delta"
TARGET = DISPATCH / f"{GAME}_子非鱼汉化{VERSION}.zip"
GAME_VERSION = "Steam 1.05（eschalon_book_1.exe，32 位）"
PLATFORM = "Steam（Windows）"
POWERSHELL = Path(os.environ["WINDIR"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def entry(source, destination, archive_path=None):
    record = {"path": destination, "sha256": digest(source), "size": source.stat().st_size}
    if archive_path:
        record["archive_path"] = archive_path
    return record


def prepare():
    assert next_version(DISPATCH, GAME) == VERSION and not ARCHIVE_OLD.exists()
    assert read_json(OLD_FILES / "PATCH_MANIFEST.json")["version"] == "1.9"
    assert read_json(BUILD / "build.json")["images"]["changed_rows"] == [60, 61, 90, 96, 99, 112, 118]
    config = read_json(ROOT / "Release/release_config.json")
    args = argparse.Namespace(
        title=TITLE, steam_url="https://store.steampowered.com/app/25600/",
        download_url=config["download_url"], mirror_url=config["mirror_url"],
        share_name=config["share_name"], feedback_name=config["feedback_name"],
        feedback_url=config["feedback_url"], game_version=GAME_VERSION, platform=PLATFORM,
        introduction="一款复古风格的单人奇幻角色扮演游戏，采用格子地图与回合制战斗。玩家自由分配属性和技能，搭配装备与法术，探索野外和地下城、寻找宝物并完成任务，在非线性冒险中揭开自己的身世。",
        coverage="剧情、对话、物品、任务、技能说明及界面文字，包含40张中文界面贴图。",
        install=f"解压到 eschalon_book_1.exe 所在文件夹，双击“{ENTRY}”，首次运行自动安装并启动，以后直接启动。",
        upgrade=f"覆盖解压新版补丁后，运行同一个“{ENTRY}”。", uninstall="运行“卸载汉化.cmd”。",
        release_date="2026-11-25", changes="润色剧情、对话、物品和界面等译文，更新快捷键、制作人员、屏幕设置和主菜单文字，并补齐新版译文所需字形。贴图改用差分安装，升级继续使用原中文版入口。",
    )
    important = f"【重要：启动中文版】\n请运行“{ENTRY}”；直接运行原游戏EXE不能启用本汉化。\n\n"
    guide = make_guide(args, VERSION, previous_changelog(DISPATCH, GAME, VERSION))
    guide = guide.replace("\n游戏介绍\n", "\n" + important + "游戏介绍\n", 1)
    assert important in guide and guide.count("v2.0（") == 1

    STAGE.mkdir()
    REPORT.mkdir(parents=True, exist_ok=True)
    helpers = {
        ENTRY: OLD_FILES / ENTRY,
        "卸载汉化.cmd": OLD_FILES / "卸载汉化.cmd",
        "汉化工具/config.json": OLD_FILES / "汉化工具/config.json",
        "汉化工具/patch.ps1": ROOT / "Release/single_entry/patch.ps1",
        "汉化工具/launch.ps1": ROOT / "Release/single_entry/launch.ps1",
    }
    installable = {
        "汉化文件/EschalonBook_Chinese_Launcher.exe": (BUILD / "EschalonBook_Chinese_Launcher.exe", RUNTIME),
        "汉化文件/steam_appid.txt": (OLD_FILES / "汉化文件/steam_appid.txt", "steam_appid.txt"),
        DELTA: (BUILD / "gfx.delta", "gfx.pak"),
    }
    for name, source in helpers.items():
        dst = STAGE / name
        dst.parent.mkdir(exist_ok=True)
        shutil.copy2(source, dst)
    (STAGE / "汉化文件").mkdir()
    for name, (source, _) in installable.items():
        shutil.copy2(source, STAGE / name)
    records = []
    for archive_path, (_, name) in installable.items():
        source = BUILD / "gfx.pak" if name == "gfx.pak" else STAGE / archive_path
        record = entry(source, name, archive_path)
        if name == "gfx.pak":
            record.update(format="eschalon-gfx-delta-v1", archive_sha256=digest(STAGE / archive_path),
                          archive_size=(STAGE / archive_path).stat().st_size, base_sha256=[ORIGINAL, V19])
        records.append(record)
    manifest = {"archive": TARGET.name, "created": args.release_date, "version": VERSION,
                "install_mode": "script", "launch_mode": "custom_launcher", "files": records,
                "auxiliary": [entry(STAGE / name, name) for name in helpers]}
    write_json(STAGE / "PATCH_MANIFEST.json", manifest)
    (STAGE / "补丁说明.txt").write_text(guide, encoding="utf-8-sig")
    files = sorted(p for p in STAGE.rglob("*") if p.is_file())
    (STAGE / "SHA256SUMS.txt").write_text("".join(
        f"{digest(p)}  {p.relative_to(STAGE).as_posix()}\n" for p in files), encoding="utf-8")
    command = [sys.executable, str(RELEASE_TOOL / "create_release_patch.py"), "--project", str(ROOT),
               "--game-name", GAME, "--title", TITLE, "--dry-run"]
    for field, value in vars(args).items():
        if field != "title":
            command.extend(("--" + field.replace("_", "-"), value))
    for path in [*helpers, *installable]:
        command.extend(("--include", f"{STAGE / path}={path}"))
    subprocess.run(command, check=True)
    cover = "https://github.com/zfyu222/eschalon-book-i-hanhua/releases/download/v2.0/title.jpg"
    notes = "![埃斯卡隆：卷一 子非鱼汉化](" + cover + ")\n\n" + guide.replace(
        "【重要：启动中文版】", "**重要：启动中文版**")
    (REPORT / "release_notes.md").write_text(notes, encoding="utf-8")


def invoke_patch(game, action="install", ok=True):
    result = subprocess.run([str(POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(game / "汉化工具/patch.ps1"), "-Action", action, "-NoLaunch"],
                            capture_output=True, timeout=90)
    if (result.returncode == 0) != ok:
        message = (result.stdout + result.stderr).decode("gbk", errors="replace")
        raise RuntimeError(message or f"{action}: exit {result.returncode}")
    return result.stdout


def assert_installed(game):
    manifest = read_json(game / "PATCH_MANIFEST.json")
    for file in manifest["files"]:
        assert digest(game / file["path"]) == file["sha256"], file["path"]
    state = read_json(game / ".zfy-localization/state.json")
    assert state["status"] == "installed" and state["package_version"] == VERSION
    return {file["path"]: (game / file["path"]).stat().st_mtime_ns for file in manifest["files"]}



def verify_player_entry(folder, actual_exe):
    game = folder / "中文 入口"
    shutil.copytree(STAGE, game)
    shutil.copy2(actual_exe, game / "eschalon_book_1.exe")
    shutil.copy2(BASE, game / "gfx.pak")
    stub = folder / "RuntimeProbe.cs"
    stub.write_text(
        'using System; using System.IO; class Probe { static void Main() { '
        'File.AppendAllText("runtime_probe.txt", '
        'Environment.GetEnvironmentVariable("ESCHALON_WINDOWED") + "|" + '
        'Environment.GetEnvironmentVariable("ESCHALON_RUNTIME") + Environment.NewLine); } }',
        encoding="ascii")
    compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework/v4.0.30319/csc.exe"
    manifest_path = game / "PATCH_MANIFEST.json"
    manifest = read_json(manifest_path)
    runtime = next(file for file in manifest["files"] if file["path"] == RUNTIME)
    stub_path = game / runtime["archive_path"]
    subprocess.run([str(compiler), "/nologo", "/target:winexe", "/out:" + str(stub_path),
                    str(stub)], capture_output=True, check=True, timeout=30)
    runtime.update(sha256=digest(stub_path), size=stub_path.stat().st_size)
    write_json(manifest_path, manifest)
    marker = game / "runtime_probe.txt"
    wanted = "1|" + str(game)
    for count in (1, 2):
        subprocess.run([str(game / ENTRY)], cwd=game, check=True, timeout=45)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if marker.exists() and len(marker.read_text(encoding="utf-8").splitlines()) == count:
                break
            time.sleep(0.2)
        assert marker.read_text(encoding="utf-8").splitlines() == [wanted] * count
        timestamps = assert_installed(game)
        if count == 1:
            previous = timestamps
        else:
            assert timestamps == previous


def verify():
    prior = OLD_FILES if not ARCHIVE_OLD.exists() else ARCHIVE_OLD
    actual_exe = ROOT / "Eschalon_CN/eschalon_book_1.exe"
    test_hash = read_json(STAGE / "汉化工具/config.json")["exe_sha256"]
    assert digest(actual_exe) == test_hash
    with TemporaryDirectory(prefix="eschalon-v20-test-") as temp:
        folder = Path(temp)

        verify_player_entry(folder, actual_exe)

        # Clean game and missing-file repair.
        game = folder / "全新 安装"
        shutil.copytree(STAGE, game)
        shutil.copy2(actual_exe, game / "eschalon_book_1.exe")
        shutil.copy2(BASE, game / "gfx.pak")
        personal = game / "test_user_settings.cfg"
        personal.write_bytes(b"settings fixture")
        invoke_patch(game)
        clean_mtimes = assert_installed(game)
        invoke_patch(game)
        assert clean_mtimes == assert_installed(game)
        (game / "gfx.pak").unlink()
        invoke_patch(game)
        assert_installed(game)
        assert digest(game / ".zfy-localization/original/gfx.pak") == ORIGINAL
        assert personal.read_bytes() == b"settings fixture"
        result = invoke_patch(game, "uninstall")
        assert b"STEAM_RESTORE=False" in result and digest(game / "gfx.pak") == ORIGINAL
        assert not (game / RUNTIME).exists()

        # Real supported prior installer and payload, using isolated copy.
        game = folder / "旧版 升级"
        shutil.copytree(prior, game)
        shutil.copy2(actual_exe, game / "eschalon_book_1.exe")
        shutil.copy2(BASE, game / "gfx.pak")
        invoke_patch(game)
        assert digest(game / "gfx.pak") == V19
        shutil.copytree(STAGE, game, dirs_exist_ok=True)
        invoke_patch(game)
        assert_installed(game)
        assert digest(game / ".zfy-localization/original/gfx.pak") == ORIGINAL
        invoke_patch(game, "uninstall")
        assert digest(game / "gfx.pak") == ORIGINAL

        # V1.6-style directly extracted localized graphics and no original backup.
        game = folder / "旧直解 升级"
        shutil.copytree(STAGE, game)
        shutil.copy2(actual_exe, game / "eschalon_book_1.exe")
        shutil.copy2(prior / "汉化文件/gfx.pak", game / "gfx.pak")
        invoke_patch(game)
        assert_installed(game)
        assert digest(game / ".zfy-localization/base/gfx.pak") == V19
        (game / "gfx.pak").unlink()
        invoke_patch(game)
        assert_installed(game)
        assert b"STEAM_RESTORE=True" in invoke_patch(game, "uninstall")

        # Corrupt package and unsupported input both stop before any writes.
        game = folder / "损坏 验证"
        shutil.copytree(STAGE, game)
        shutil.copy2(actual_exe, game / "eschalon_book_1.exe")
        shutil.copy2(BASE, game / "gfx.pak")
        (game / DELTA).write_bytes(b"corrupt")
        invoke_patch(game, ok=False)
        assert digest(game / "gfx.pak") == ORIGINAL and not (game / RUNTIME).exists()
        shutil.copy2(STAGE / DELTA, game / DELTA)
        (game / "gfx.pak").write_bytes(b"unknown")
        invoke_patch(game, ok=False)
        assert (game / "gfx.pak").read_bytes() == b"unknown" and not (game / RUNTIME).exists()
    data = read_json(BUILD / "build.json")
    data.update(status="passed", player_entry_replayed=True, clean_install=True, repair_missing=True, no_rewrite=True,
                upgrade_v19=True, upgrade_legacy_no_original=True, uninstall=True,
                corrupt_input_rejected=True, unsupported_base_rejected=True,
                in_game_validation="pending")
    write_json(REPORT / "build_and_install.json", data)
    print(json.dumps({"installation_replay": "passed", "in_game_validation": "pending"}))


def package():
    assert read_json(REPORT / "build_and_install.json")["status"] == "passed"
    assert read_json(REPORT / "visual_review.json")["status"] == "passed"
    assert not TARGET.exists() and not ARCHIVE_OLD.exists()
    manifest = read_json(STAGE / "PATCH_MANIFEST.json")
    sys.path.insert(0, str(WORKSPACE / "Tools/localization"))
    from translation_workflow import Workflow
    flow = Workflow(ROOT)
    approval_path = REPORT / "release_instruction.json"
    write_json(approval_path, {"user_statement": "发布", "date": "2026-11-25",
                               "context": "直接接续用户收到的译表交付，上一条答复说明回填和实机验证待后续进行。",
                               "in_game_validation": "pending", "version": VERSION})
    authorized = {}
    for item in manifest["files"] + manifest["auxiliary"]:
        archive_path = item.get("archive_path", item["path"])
        source = BUILD / "gfx.pak" if item["path"] == "gfx.pak" else STAGE / archive_path
        assert digest(source) == item["sha256"]
        authorized[item["path"]] = source
    authorized[DELTA] = STAGE / DELTA

    def bound(path, game_path=None):
        proof = {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)}
        if game_path:
            proof["game_path"] = game_path
        return proof

    flow.record_release_acceptance({
        "translation_sha256": read_json(BUILD / "build.json")["translation_sha256"],
        "authorization": "explicit_user_release", "in_game_validation": "pending",
        "accept_pending_runtime": True, "user_statement": "发布",
        "game_version": GAME_VERSION, "platform": PLATFORM,
        "payload_files": [bound(path, dest) for dest, path in authorized.items()],
        "evidence_files": [bound(REPORT / name) for name in
                           ("release_instruction.json", "build_and_install.json", "visual_review.json")],
    })
    result = flow.release_check()
    assert result["status"] == "passed"
    write_json(REPORT / "release_check.json", result)
    ARCHIVE_OLD.parent.mkdir(exist_ok=True)
    OLD_FILES.rename(ARCHIVE_OLD)
    try:
        shutil.copytree(STAGE, OLD_FILES)
        expected = {e.get("archive_path", e["path"]) for e in manifest["files"] + manifest["auxiliary"]}
        expected.update(("补丁说明.txt", "PATCH_MANIFEST.json", "SHA256SUMS.txt"))
        assert {p.relative_to(OLD_FILES).as_posix() for p in OLD_FILES.rglob("*") if p.is_file()} == expected
        candidate = BUILD / TARGET.name
        with zipfile.ZipFile(candidate, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(expected):
                archive.write(OLD_FILES / name, name)
        with zipfile.ZipFile(candidate) as archive:
            assert archive.testzip() is None and set(archive.namelist()) == expected
            for line in archive.read("SHA256SUMS.txt").decode("utf-8").splitlines():
                expected_hash, name = line.split("  ", 1)
                assert sha(archive.read(name)) == expected_hash
        candidate.rename(TARGET)
    except Exception:
        if OLD_FILES.exists():
            OLD_FILES.rename(BUILD / "failed_dispatch_staging")
        ARCHIVE_OLD.rename(OLD_FILES)
        raise
    for name in ("补丁说明.txt", "PATCH_MANIFEST.json", "SHA256SUMS.txt"):
        shutil.copy2(OLD_FILES / name, DISPATCH / name)
    config = ROOT / "Release/release_config.json"
    write_json(config, {**read_json(config), "version": VERSION})
    info = {"status": "passed", "version": VERSION, "archive": TARGET.name,
            "size": TARGET.stat().st_size, "sha256": digest(TARGET), "entries": len(expected),
            "crc_and_checksums": True, "in_game_validation": "pending"}
    write_json(REPORT / "package.json", info)
    print(json.dumps(info, ensure_ascii=False))


def deploy():
    game = (ROOT / "Game").resolve(strict=True)
    current = read_json(game / ".zfy-localization/state.json")
    assert current["package_version"] == "1.9" and read_json(REPORT / "package.json")["status"] == "passed"
    assert digest(game / ".zfy-localization/original/gfx.pak") == ORIGINAL
    config = read_json(STAGE / "汉化工具/config.json")
    assert digest(game / config["exe"]) == config["exe_sha256"]
    subprocess.run([str(POWERSHELL), "-NoProfile", "-Command",
                    "if (Get-Process -Name eschalon_book_1 -ErrorAction SilentlyContinue) { exit 23 }"],
                   check=True, timeout=30)
    backup = BUILD / "local_previous"
    backup.mkdir()
    manifest = read_json(STAGE / "PATCH_MANIFEST.json")
    names = {p.relative_to(STAGE).as_posix() for p in STAGE.rglob("*") if p.is_file()}
    names.update(file["path"] for file in manifest["files"])
    names.add(".zfy-localization/state.json")
    for name in sorted(names):
        source = game / name
        if source.is_file():
            saved = backup / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, saved)
    saves = Path.home() / "Documents/Eschalon Book 1 Saved Games"
    personal = {path: digest(path) for path in saves.rglob("*") if path.is_file()}
    shutil.copytree(STAGE, game, dirs_exist_ok=True)
    invoke_patch(game)
    installed = assert_installed(game)
    assert personal == {path: digest(path) for path in saves.rglob("*") if path.is_file()}
    assert digest(game / ".zfy-localization/original/gfx.pak") == ORIGINAL
    write_json(REPORT / "local_deploy.json", {"status": "passed", "version": VERSION,
               "installed": sorted(installed), "version_before": current["package_version"],
               "original_retained": True, "saved_game_files_verified": len(personal),
               "game_started": False, "in_game_validation": "pending"})
    print("Local installation verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    phases = {"prepare": prepare, "verify": verify, "package": package, "deploy": deploy}
    parser.add_argument("phase", choices=phases)
    phases[parser.parse_args().phase]()
