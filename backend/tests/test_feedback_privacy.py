"""The feedback tracker may be public: issues must never expose who filed them."""

from unittest.mock import MagicMock, patch

from app.services.github_service import GitHubService


def _captured_issue(**kwargs) -> dict:
    service = GitHubService()
    service.token, service.repo = "t", "owner/repo"
    response = MagicMock()
    response.json.return_value = {"html_url": "https://github.com/owner/repo/issues/1"}
    with patch("app.services.github_service.httpx.post", return_value=response) as post:
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
