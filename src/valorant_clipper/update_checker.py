from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass

from .build_info import BUILD_DATE, BUILD_SHA


REPO = "jiashusu/valorant-highlight-clipper"
BRANCH = "main"
REPO_URL = f"https://github.com/{REPO}"
DOWNLOAD_URL = f"{REPO_URL}/actions/workflows/build-desktop.yml"


@dataclass
class UpdateResult:
    current_sha: str
    remote_sha: str | None
    update_available: bool
    message: str
    download_url: str = DOWNLOAD_URL

    @property
    def current_short(self) -> str:
        return short_sha(self.current_sha)

    @property
    def remote_short(self) -> str:
        return short_sha(self.remote_sha or "")


def short_sha(value: str) -> str:
    if not value or value == "unknown":
        return "unknown"
    return value[:7]


def check_for_update() -> UpdateResult:
    current_sha = BUILD_SHA.strip() or "unknown"
    remote_sha = fetch_remote_sha()
    if current_sha == "unknown":
        return UpdateResult(
            current_sha=current_sha,
            remote_sha=remote_sha,
            update_available=False,
            message=f"当前 App 没有打包版本信息。最新提交: {short_sha(remote_sha)}",
        )

    if remote_sha.startswith(current_sha) or current_sha.startswith(remote_sha):
        return UpdateResult(
            current_sha=current_sha,
            remote_sha=remote_sha,
            update_available=False,
            message=f"已经是最新版本。当前: {short_sha(current_sha)}，打包时间: {BUILD_DATE}",
        )

    return UpdateResult(
        current_sha=current_sha,
        remote_sha=remote_sha,
        update_available=True,
        message=f"发现新版本。当前: {short_sha(current_sha)}，最新: {short_sha(remote_sha)}",
    )


def fetch_remote_sha() -> str:
    errors: list[str] = []
    try:
        return fetch_remote_sha_public()
    except Exception as exc:
        errors.append(f"GitHub API: {exc}")

    try:
        return fetch_remote_sha_with_gh()
    except Exception as exc:
        errors.append(f"gh CLI: {exc}")

    raise RuntimeError("无法检查更新。" + "；".join(errors))


def fetch_remote_sha_public() -> str:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/commits/{BRANCH}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ValorantHighlightClipper",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    sha = str(payload.get("sha", "")).strip()
    if not sha:
        raise RuntimeError("response missing sha")
    return sha


def fetch_remote_sha_with_gh() -> str:
    gh_path = find_gh()
    if not gh_path:
        raise RuntimeError("未找到 gh 命令")

    result = subprocess.run(
        [gh_path, "api", f"repos/{REPO}/commits/{BRANCH}", "--jq", ".sha"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        env=github_cli_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gh api failed")
    sha = result.stdout.strip()
    if not sha:
        raise RuntimeError("gh response missing sha")
    return sha


def find_gh() -> str | None:
    candidates = [
        shutil.which("gh"),
        "/opt/homebrew/bin/gh",
        "/usr/local/bin/gh",
        "/usr/bin/gh",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def github_cli_env() -> dict[str, str]:
    env = os.environ.copy()
    paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    env["PATH"] = os.pathsep.join(paths + [env.get("PATH", "")])
    return env
