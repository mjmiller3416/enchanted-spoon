"""The feedback tracker may be public: issues must never expose who filed them."""

from unittest.mock import MagicMock, patch

from app.services.github_service import GitHubService


def _captured_issue(**kwargs) -> dict:
    service = GitHubService()
    service.token, service.repo = "t", "owner/repo"
    response = MagicMock()
    response.json.return_value = {"html_url": "https://github.com/owner/repo/issues/1"}
    repository = MagicMock()
    repository.json.return_value = {"private": True}
    with patch("app.services.github_service.httpx.get", return_value=repository), patch("app.services.github_service.httpx.post", return_value=response) as post:
        service.create_issue(**kwargs)
    return post.call_args.kwargs["json"]


def test_issue_identifies_user_by_id_not_email():
    issue = _captured_issue(
        category="Bug Report", message="Planner froze on save", user_ref="user #42"
    )
    assert "user #42" in issue["body"]
    assert "@" not in issue["body"].replace("@​", "")


def test_mentions_and_markdown_in_message_are_inert():
    issue = _captured_issue(
        category="Bug Report",
        message="cc @octocat ![x](https://evil.example/p.png) ~~~ break out",
        user_ref="user #1",
    )
    body = issue["body"]
    assert "@octocat" not in body and "@​octocat" in body
    # Message sits inside a single fenced block that it cannot close early
    assert body.count("~~~") == 2
    assert "@octocat" not in issue["title"]


def test_only_allowlisted_metadata_is_published_and_capped():
    issue = _captured_issue(
        category="Bug Report",
        message="Something broke here",
        user_ref="user #1",
        metadata={"page_url": "/recipes\n## injected", "secret": "x", "viewport": "v" * 500},
    )
    body = issue["body"]
    assert "secret" not in body
    assert "\n## injected" not in body
    assert "v" * 201 not in body


def test_feedback_does_not_publish_url_secrets():
    issue = _captured_issue(category="Bug Report", message="Something broke", user_ref="user #1",
                            metadata={"page_url": "https://user:password@example.com/recipes?token=secret#private"})
    assert "`/recipes`" in issue["body"]
    for private in ("password", "token", "secret", "private", "example.com"):
        assert private not in issue["body"]


def test_unconfigured_feedback_does_not_claim_delivery():
    import pytest
    from app.services.github_service import GitHubIssueError
    service = GitHubService()
    service.token = service.repo = ""
    with pytest.raises(GitHubIssueError):
        service.create_issue(category="Bug Report", message="Something broke", user_ref="user #1")


def test_public_or_unknown_tracker_never_receives_feedback():
    import pytest
    from app.services.github_service import GitHubIssueError
    for visibility in (False, None):
        service = GitHubService()
        service.token, service.repo = "dummy", "owner/repo"
        repository = MagicMock()
        repository.json.return_value = {"private": visibility}
        with patch("app.services.github_service.httpx.get", return_value=repository), patch("app.services.github_service.httpx.post") as post:
            with pytest.raises(GitHubIssueError):
                service.create_issue(category="Question", message="Private message", user_ref="user #1")
            post.assert_not_called()
