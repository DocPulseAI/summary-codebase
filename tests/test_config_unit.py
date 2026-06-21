import importlib


def _reload_module():
    import src.config as cfg
    return importlib.reload(cfg)


def test_config_validate_raises_when_git_required_and_env_missing(monkeypatch):
    monkeypatch.delenv("REPO_OWNER", raising=False)
    monkeypatch.delenv("REPO_NAME", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    cfg = _reload_module()

    try:
        cfg.Config.validate(require_git=True)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "REPO_OWNER" in str(exc)
        assert "REPO_NAME" in str(exc)
        assert "GITHUB_TOKEN" in str(exc)


def test_config_validate_passes_when_git_not_required(monkeypatch):
    monkeypatch.delenv("REPO_OWNER", raising=False)
    monkeypatch.delenv("REPO_NAME", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    cfg = _reload_module()
    cfg.Config.validate(require_git=False)


def test_config_reads_mode_defaults(monkeypatch):
    monkeypatch.delenv("MODE", raising=False)
    monkeypatch.delenv("EPIC4_MODE", raising=False)

    cfg = _reload_module()
    assert cfg.Config.EXECUTION_MODE == "FULL_MODE"
