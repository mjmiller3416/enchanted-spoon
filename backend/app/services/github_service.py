"""GitHub issue creation service for user feedback."""

import logging
import os
import re
from urllib.parse import urlsplit
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CATEGORY_TO_LABEL = {
    "Bug Report": "bug",
    "Feature Request": "enhancement",
    "General Feedback": "feedback",
    "Question": "question",
}


# Only these context keys are published, each capped, so a client can't use
# the metadata dict to push arbitrary content into the (public) issue tracker
ALLOWED_METADATA_KEYS = ("page_url", "viewport", "user_agent", "app_version")
MAX_METADATA_VALUE_LENGTH = 200


def _neutralize_mentions(text: str) -> str:
    """Stop @user / @org/team in user text from pinging anyone on GitHub."""
    return re.sub(r"@(?=[A-Za-z0-9])", "@\u200b", text)


def _as_plain_text_block(text: str) -> str:
    """Render user text verbatim: no links, images, or markdown in the issue."""
    return "~~~text\n" + text.replace("~~~", "~ ~ ~") + "\n~~~"


class GitHubIssueError(Exception):
    """Raised when GitHub issue creation fails."""

    pass


class GitHubService:
    """Creates GitHub issues from user feedback submissions."""

    def __init__(self) -> None:
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.repo = os.getenv("GITHUB_REPO", "")

    @property
    def _configured(self) -> bool:
        return bool(self.token and self.repo)

    def create_issue(
        self,
        category: str,
        message: str,
        user_ref: str,
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Create a GitHub issue from user feedback.

        The issue tracker may be public, so the submitter is identified only
        by ``user_ref`` (an opaque internal id), never their email, and the
        message is published as a plain-text block.

        Returns the issue URL on success. Missing configuration fails explicitly.

        Raises:
            GitHubIssueError: If the API call fails.
        """
        if not self._configured:
            logger.warning("GITHUB_TOKEN or GITHUB_REPO not set — skipping issue creation")
            raise GitHubIssueError("Feedback delivery is unavailable")

        # Free text must never be automatically published to a public tracker.
        # Check the actual destination on every submission; configuration alone
        # is not evidence of its visibility. A failed lookup fails closed.
        try:
            repository = httpx.get(
                f"https://api.github.com/repos/{self.repo}",
                headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"},
                timeout=10.0,
            )
            repository.raise_for_status()
            if repository.json().get("private") is not True:
                raise GitHubIssueError("Feedback requires a private support destination")
        except (httpx.HTTPError, ValueError) as exc:
            raise GitHubIssueError("Unable to verify private feedback delivery") from exc

        label = CATEGORY_TO_LABEL.get(category, "feedback")
        summary = " ".join(message.split())[:80]
        title = _neutralize_mentions(f"[{category}] {summary}")

        body_parts = [
            f"**Category:** {category}",
            f"**Submitted by:** {user_ref}",
            "",
            "---",
            "",
            _as_plain_text_block(_neutralize_mentions(message)),
        ]

        metadata = dict(metadata or {})
        if "page_url" in metadata:
            # Publish only a path: queries/fragments may contain auth or user data.
            try:
                metadata["page_url"] = urlsplit(str(metadata["page_url"])).path
            except ValueError:
                metadata.pop("page_url", None)
        context = [
            (key, " ".join(str(metadata[key]).split())[:MAX_METADATA_VALUE_LENGTH])
            for key in ALLOWED_METADATA_KEYS
            if metadata and metadata.get(key) is not None
        ]
        if context:
            body_parts.extend(["", "---", "", "**Context:**"])
            for key, value in context:
                safe_value = value.replace("`", "'")
                body_parts.append(f"- **{key}:** `{safe_value}`")

        body = "\n".join(body_parts)

        try:
            resp = httpx.post(
                f"https://api.github.com/repos/{self.repo}/issues",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={
                    "title": title,
                    "body": body,
                    "labels": [label, "user-feedback"],
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()["html_url"]
        except httpx.HTTPStatusError as e:
            logger.error("GitHub API error %s", e.response.status_code)
            raise GitHubIssueError(f"GitHub API returned {e.response.status_code}") from e
        except httpx.HTTPError as e:
            logger.error("GitHub API request failed: %s", e)
            raise GitHubIssueError("Failed to reach GitHub API") from e
