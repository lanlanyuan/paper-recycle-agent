"""历史校验器自身的测试。

一个校验器如果永远只会说「通过」，那它就是装饰品。这里在临时仓库里
刻意造出各类违规历史，确认 check_history 能一条条抓出来。
"""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_history  # noqa: E402

pytestmark = pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="需要 git",
)

ENV_BASE = {
    "GIT_AUTHOR_NAME": "tester",
    "GIT_AUTHOR_EMAIL": "tester@example.com",
    "GIT_COMMITTER_NAME": "tester",
    "GIT_COMMITTER_EMAIL": "tester@example.com",
}


def git(repo, *args, env=None):
    full_env = os.environ.copy()
    full_env.update(ENV_BASE)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["git"] + list(args),
        cwd=str(repo),
        env=full_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def make_repo(path):
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", "tester")
    git(path, "config", "user.email", "tester@example.com")
    git(path, "config", "commit.gpgsign", "false")
    return path


def commit(repo, message, when, filename=None):
    # 文件名必须每次唯一：用 glob 数量推算会在切分支后重复，
    # 造成「两个分支改了同一个文件」的假冲突，让 merge 静默失败。
    name = filename or ("f_%s.txt" % uuid.uuid4().hex[:8])
    (repo / name).write_text(message, encoding="utf-8")
    git(repo, "add", name)
    proc = git(
        repo, "commit", "-q", "-m", message,
        env={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when},
    )
    # 助手静默失败会让测试得出错误结论，这里必须炸出来
    assert proc.returncode == 0, "git commit 失败：%s" % proc.stderr
    return proc


def merge_no_ff(repo, branch, message):
    proc = git(repo, "merge", "--no-ff", "-m", message, branch)
    assert proc.returncode == 0, "git merge 失败：%s%s" % (proc.stdout, proc.stderr)
    return proc


def load(repo, monkeypatch):
    """在指定仓库里重新采集数据（校验器依赖 cwd 调用 git）。"""
    monkeypatch.chdir(repo)
    commits = check_history._commits()
    parents = check_history._parents()
    return commits, parents


# ------------------------------------------------------------------ 正常历史

def test_clean_history_passes(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "clean")
    commit(repo, "feat: 第一个功能", "2026-01-01T10:00:00+0800")
    commit(repo, "fix: 修一个问题", "2026-01-02T10:00:00+0800")
    commits, parents = load(repo, monkeypatch)

    assert check_history.check_time_order(commits, parents) == []
    assert check_history.check_author_equals_committer(commits) == []
    assert check_history.check_subject_prefix(commits) == []


# ------------------------------------------------------------------ 时间倒挂

def test_detects_child_older_than_parent(tmp_path, monkeypatch):
    """发布提交比它要发布的内容还早 —— 这是最典型的"改过历史"痕迹。"""
    repo = make_repo(tmp_path / "reversed")
    commit(repo, "feat: 内容", "2026-02-10T10:00:00+0800")
    commit(repo, "chore: 发布", "2026-02-09T10:00:00+0800")
    commits, parents = load(repo, monkeypatch)

    problems = check_history.check_time_order(commits, parents)
    assert problems, "子提交早于父提交必须被报出来"
    assert "时间倒挂" in problems[0]


def test_detects_author_committer_mismatch(tmp_path, monkeypatch):
    """author 与 committer 不一致，通常是只改了其中一个时间。"""
    repo = make_repo(tmp_path / "mismatch")
    (repo / "a.txt").write_text("x", encoding="utf-8")
    git(repo, "add", "a.txt")
    git(
        repo, "commit", "-q", "-m", "feat: 不一致",
        env={
            "GIT_AUTHOR_DATE": "2026-03-01T10:00:00+0800",
            "GIT_COMMITTER_DATE": "2026-03-02T10:00:00+0800",
        },
    )
    commits, _ = load(repo, monkeypatch)

    problems = check_history.check_author_equals_committer(commits)
    assert problems
    assert "不一致" in problems[0]


def test_detects_future_timestamp(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "future")
    commit(repo, "feat: 来自未来", "2099-01-01T10:00:00+0800")
    commits, _ = load(repo, monkeypatch)

    problems = check_history.check_no_future(commits)
    assert problems
    assert "未来" in problems[0]


# ------------------------------------------------------- 分支与合并轨迹

def test_detects_branch_without_merge_commit(tmp_path, monkeypatch):
    """feature 分支被快进合并（或根本没合并），合并轨迹就丢了。"""
    repo = make_repo(tmp_path / "ff")
    commit(repo, "feat: 主干起点", "2026-04-01T10:00:00+0800")
    git(repo, "checkout", "-q", "-b", "feature/ghost")
    commit(repo, "feat: 分支上的改动", "2026-04-02T10:00:00+0800")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "--ff-only", "feature/ghost")  # 快进：没有 merge commit

    monkeypatch.chdir(repo)
    problems, merge_count = check_history.check_merge_commits(check_history._parents())
    assert merge_count == 0
    assert any("feature/ghost" in p for p in problems)


def test_no_ff_merge_is_recognised(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "noff")
    commit(repo, "feat: 主干起点", "2026-05-01T10:00:00+0800")
    git(repo, "checkout", "-q", "-b", "feature/real")
    commit(repo, "feat: 分支上的改动", "2026-05-02T10:00:00+0800")
    git(repo, "checkout", "-q", "main")
    commit(repo, "docs: 主干继续", "2026-05-03T10:00:00+0800")
    merge_no_ff(repo, "feature/real", "Merge PR #1: 分支")

    monkeypatch.chdir(repo)
    problems, merge_count = check_history.check_merge_commits(check_history._parents())
    assert merge_count == 1
    assert problems == []


# ------------------------------------------------------------------ 提交信息

def test_detects_missing_prefix(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "prefix")
    commit(repo, "随便写了点东西", "2026-06-01T10:00:00+0800")
    commits, _ = load(repo, monkeypatch)

    problems = check_history.check_subject_prefix(commits)
    assert problems
    assert "前缀" in problems[0]


def test_merge_commit_exempt_from_prefix(tmp_path, monkeypatch):
    """git 自动生成的 Merge 提交不该被要求加 feat/fix 前缀。"""
    repo = make_repo(tmp_path / "mergeok")
    commit(repo, "feat: a", "2026-07-01T10:00:00+0800")
    commit(repo, "Merge PR #2: 合并", "2026-07-02T10:00:00+0800")
    commits, _ = load(repo, monkeypatch)

    assert check_history.check_subject_prefix(commits) == []


# ------------------------------------------------------------------ 退出码

def test_main_returns_nonzero_on_dirty_history(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path / "exitcode")
    commit(repo, "feat: 内容", "2026-08-10T10:00:00+0800")
    commit(repo, "chore: 发布", "2026-08-09T10:00:00+0800")
    monkeypatch.chdir(repo)

    code = check_history.main([])
    out = capsys.readouterr().out
    assert code == 1
    assert "不通过" in out


def test_main_returns_zero_on_clean_history(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path / "exitok")
    commit(repo, "feat: 内容", "2026-09-01T10:00:00+0800")
    monkeypatch.chdir(repo)

    code = check_history.main(["--quiet"])
    assert code == 0
