#!/usr/bin/env python3
"""Private GitHub main mirror with independent remote checkout verification.

Pattern read from agent-quota-launcher/scripts/backup.py. No tokens are
copied from that project. gh uses the operator's existing auth.
"""
import argparse
import datetime
import fcntl
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def call(args, **kw):
    proc = subprocess.run(args, capture_output=True, text=True, timeout=120, **kw)
    if proc.returncode:
        raise RuntimeError(f"{args[:2]} failed (exit {proc.returncode})")
    return proc.stdout.strip()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="alexeygrigorev/agent-coordination")
    args = parser.parse_args()
    local = ROOT / ".local"
    local.mkdir(exist_ok=True, mode=0o700)
    if shutil.disk_usage("/").free < 50 * 1024**3 + 512 * 1024**2:
        raise RuntimeError("backup restore requires 50GiB free plus 512MiB spike")
    lock = open(local / "git.lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX)
    if call(["git", "branch", "--show-current"], cwd=ROOT) != "main":
        raise RuntimeError("backup only main")
    sha = call(["git", "rev-parse", "HEAD"], cwd=ROOT)
    viewed = subprocess.run(
        ["gh", "repo", "view", args.repo, "--json", "isPrivate,url"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if viewed.returncode:
        call(
            [
                "gh",
                "repo",
                "create",
                args.repo,
                "--private",
                "--description",
                "Cross-computer agent coordination over authenticated SSH",
            ]
        )
        viewed = subprocess.run(
            ["gh", "repo", "view", args.repo, "--json", "isPrivate,url"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    info = json.loads(viewed.stdout)
    if info["isPrivate"] is not True:
        raise RuntimeError("backup repository is not private")
    url = "https://github.com/" + args.repo + ".git"
    call(["git", "push", url, "HEAD:refs/heads/main"], cwd=ROOT)
    remote_sha = call(["git", "ls-remote", url, "refs/heads/main"]).split()[0]
    if remote_sha != sha:
        raise RuntimeError("mirror ref mismatch")
    dest = pathlib.Path(tempfile.mkdtemp(prefix="restore-", dir=local))
    call(["git", "clone", "--quiet", "--single-branch", "--branch", "main", url, str(dest)])
    restored = call(["git", "rev-parse", "HEAD"], cwd=dest)
    if restored != sha:
        raise RuntimeError("restore mismatch")
    call(["git", "fsck", "--no-reflogs"], cwd=dest)
    result = {
        "repo": info["url"],
        "private": True,
        "main": sha,
        "restored_sha": restored,
        "restore_path": str(dest),
        "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "fsck": "passed",
        "method": "remote-github-clone",
    }
    (local / "backup-evidence.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
