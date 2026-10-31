"""Extract recipe text from a public TikTok or Instagram post.

Official oEmbed is the only metadata source:

- TikTok's public oEmbed endpoint needs no key. Its ``title`` is the caption.
- Instagram's oEmbed is Meta's free oEmbed Read API and needs an app token
  (``INSTAGRAM_OEMBED_ACCESS_TOKEN``). Without that token we read only the
  public page's Open Graph description.

Neither endpoint includes a spoken transcript, and this module does not
download video, scrape private page state, or call a paid transcript vendor.
A post whose recipe exists only in the audio fails with "no recipe found"
after the caption is normalized by the existing import prompt.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.ai.recipe_import.config import FETCH_HEADERS, FETCH_TIMEOUT_SECONDS

# Meta's official Instagram oEmbed. Free for an app with the oEmbed Read
# feature; not a paid third-party scraper. Stubbed until the token is set.
INSTAGRAM_OEMBED_TOKEN_ENV = "INSTAGRAM_OEMBED_ACCESS_TOKEN"
INSTAGRAM_OEMBED_URL = "https://graph.facebook.com/v21.0/instagram_oembed"
TIKTOK_OEMBED_URL = "https://www.tiktok.com/oembed"

TIKTOK_HOSTS = {
    "tiktok.com",
    "www.tiktok.com",
    "m.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
}
INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
SHORT_TIKTOK_HOSTS = {"vm.tiktok.com", "vt.tiktok.com"}

MAX_CAPTION_CHARS = 8000
MAX_OEMBED_BYTES = 1024 * 1024


class SocialExtractError(Exception):
    """A social URL could not be turned into caption text.

    ``kind`` is ``fetch`` (private, unsupported, unreachable) or ``not_found``
    (the post was readable but had no caption to search).
    """

    def __init__(self, message: str, kind: str = "fetch") -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class SocialPost:
    """Caption and public metadata for one post or reel."""

    platform: str
    caption: str
    author_name: Optional[str] = None
    thumbnail_url: Optional[str] = None


def classify_social_url(url: str) -> Optional[str]:
    """Return ``tiktok`` or ``instagram`` when ``url`` is a post on those hosts."""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if host in TIKTOK_HOSTS:
        return "tiktok"
    if host in INSTAGRAM_HOSTS:
        return "instagram"
    return None


def _path_parts(url: str) -> list[str]:
    parsed = urlparse(url.strip())
    return [part for part in (parsed.path or "").split("/") if part]


def assert_content_url(url: str, platform: str) -> None:
    """Reject profile and home URLs so we never invent a recipe from a bio."""
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    parts = _path_parts(url)
    if platform == "tiktok":
        if host in SHORT_TIKTOK_HOSTS and parts:
            return
        if "video" in parts or "photo" in parts or (parts and parts[0] == "t"):
            return
        raise SocialExtractError(
            "Paste a link to a specific TikTok video, not a profile."
        )
    if parts and parts[0] in {"p", "reel", "reels", "tv", "share"}:
        return
    raise SocialExtractError(
        "Paste a link to a specific Instagram post or reel, not a profile."
    )


def _caption_from_oembed(payload: dict) -> str:
    title = str(payload.get("title") or "").strip()
    if title:
        return title[:MAX_CAPTION_CHARS]
    html = str(payload.get("html") or "")
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return text[:MAX_CAPTION_CHARS]


def _post_from_oembed(platform: str, payload: dict) -> SocialPost:
    caption = _caption_from_oembed(payload)
    if not caption:
        raise SocialExtractError(
            "That post didn't include a caption, so there is no recipe text to import.",
            kind="not_found",
        )
    thumbnail = payload.get("thumbnail_url")
    thumbnail_url = thumbnail if isinstance(thumbnail, str) and thumbnail.startswith("http") else None
    author = payload.get("author_name")
    return SocialPost(
        platform=platform,
        caption=caption,
        author_name=author if isinstance(author, str) and author.strip() else None,
        thumbnail_url=thumbnail_url,
    )


def _private_message(platform: str) -> str:
    name = "TikTok" if platform == "tiktok" else "Instagram"
    return (
        f"That {name} post is private, deleted, or not available. "
        "Ask for a public post link and try again."
    )


def parse_oembed_response(platform: str, status_code: int, body: bytes) -> SocialPost:
    """Turn an oEmbed HTTP response into a post, or a user-facing error."""
    if status_code in (400, 401, 403, 404):
        raise SocialExtractError(_private_message(platform))
    if status_code >= 400:
        raise SocialExtractError("That post could not be loaded. Please try again.")
    if len(body) > MAX_OEMBED_BYTES:
        raise SocialExtractError("That post's metadata was too large to import.")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SocialExtractError(
            "That post's metadata could not be read. Please try again."
        ) from exc
    if not isinstance(payload, dict):
        raise SocialExtractError("That post's metadata could not be read. Please try again.")
    return _post_from_oembed(platform, payload)


def parse_instagram_html(status_code: int, html: str) -> SocialPost:
    """Read a caption from public Open Graph tags. Login walls are a fetch error."""
    if status_code in (401, 403, 404):
        raise SocialExtractError(_private_message("instagram"))
    if status_code >= 400:
        raise SocialExtractError(
            "Instagram didn't return that post. It may be private, or the link may be wrong."
        )

    soup = BeautifulSoup(html or "", "html.parser")
    description = _meta(soup, "og:description") or _meta(soup, "description")
    title = _meta(soup, "og:title")
    image = _meta(soup, "og:image")
    lowered = (html or "").lower()
    login_wall = "login" in lowered and not description
    generic = (description or "").strip().lower() in {
        "",
        "instagram",
        "see instagram photos and videos from your friends.",
    }
    if login_wall or generic:
        raise SocialExtractError(
            "Instagram didn't share that caption. The post may be private. "
            "A public post works once the server has INSTAGRAM_OEMBED_ACCESS_TOKEN "
            "(Meta's free oEmbed), or when the page exposes a description."
        )

    caption = (description or title or "").strip()[:MAX_CAPTION_CHARS]
    if not caption:
        raise SocialExtractError(
            "That post didn't include a caption, so there is no recipe text to import.",
            kind="not_found",
        )
    thumbnail = image if image and image.startswith("http") else None
    return SocialPost(platform="instagram", caption=caption, thumbnail_url=thumbnail)


def _meta(soup: BeautifulSoup, key: str) -> Optional[str]:
    tag = soup.find("meta", property=key) or soup.find("meta", attrs={"name": key})
    if tag is None:
        return None
    content = tag.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None


def source_block_for(post: SocialPost) -> str:
    """Text block the existing recipe-import prompt can normalize."""
    lines = [
        f"Caption and public metadata from a {post.platform} post.",
        "Extract a recipe only when the caption contains one.",
        "Do not invent ingredients or steps that are not written here.",
        "A spoken-only recipe with no written ingredients is not a recipe.",
    ]
    if post.author_name:
        lines.append(f"Author: {post.author_name}")
    lines.append("Caption:")
    lines.append(post.caption)
    return "\n".join(lines)


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    from app.services.ai.recipe_import.service import RecipeImportService

    return await RecipeImportService._fetch_following_validated_redirects(client, url)


async def fetch_social_post(url: str) -> SocialPost:
    """Fetch caption metadata for a TikTok or Instagram content URL.

    Raises:
        SocialExtractError: The post is private, not a content URL, or has no caption.
    """
    platform = classify_social_url(url)
    if platform is None:
        raise SocialExtractError("That link is not a TikTok or Instagram post.")
    assert_content_url(url, platform)

    from app.services.ai.recipe_import.service import (  # local: transport lives there
        RecipeImportFetchError,
        _PublicOnlyTransport,
    )

    try:
        async with httpx.AsyncClient(
            headers=FETCH_HEADERS,
            follow_redirects=False,
            timeout=FETCH_TIMEOUT_SECONDS,
            transport=_PublicOnlyTransport(),
        ) as client:
            if platform == "tiktok":
                oembed_url = f"{TIKTOK_OEMBED_URL}?url={quote(url, safe='')}"
                response = await _get(client, oembed_url)
                return parse_oembed_response(platform, response.status_code, response.content)

            token = os.getenv(INSTAGRAM_OEMBED_TOKEN_ENV, "").strip()
            if token:
                oembed_url = (
                    f"{INSTAGRAM_OEMBED_URL}?url={quote(url, safe='')}"
                    f"&access_token={quote(token, safe='')}&omitscript=true"
                )
                response = await _get(client, oembed_url)
                return parse_oembed_response(platform, response.status_code, response.content)

            response = await _get(client, url)
            return parse_instagram_html(response.status_code, response.text)
    except SocialExtractError:
        raise
    except RecipeImportFetchError as exc:
        raise SocialExtractError(str(exc)) from exc
    except httpx.TimeoutException as exc:
        raise SocialExtractError(
            "That post took too long to load. Please try again."
        ) from exc
    except httpx.HTTPError as exc:
        raise SocialExtractError(
            "That post could not be reached. Check the link and try again."
        ) from exc
