"""TikTok and Instagram recipe import.

Caption extraction is tested without the network. The service test checks that
a social URL reuses the existing normalizer and that private posts and
caption-less posts surface as the same errors as a bad website import.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.dtos.recipe_generation_dtos import RecipeGeneratedDTO
from app.dtos.recipe_import_dtos import RecipeImportRequestDTO
from app.services.ai.recipe_import.service import (
    RecipeImportFetchError,
    RecipeImportNotFoundError,
    RecipeImportService,
)
from app.services.ai.recipe_import.social import (
    SocialExtractError,
    assert_content_url,
    classify_social_url,
    parse_instagram_html,
    parse_oembed_response,
    source_block_for,
)

pytestmark = pytest.mark.anyio


def anyio_backend():
    return "asyncio"


def _recipe() -> RecipeGeneratedDTO:
    return RecipeGeneratedDTO(
        recipe_name="Chili Garlic Noodles",
        recipe_category="other",
        ingredients=[],
        directions="Boil noodles.",
    )


class TestSocialUrlClassification:
    @pytest.mark.parametrize(
        "url,platform",
        [
            ("https://www.tiktok.com/@chef/video/123", "tiktok"),
            ("https://vm.tiktok.com/ZMabc123/", "tiktok"),
            ("https://www.instagram.com/reel/ABC123/", "instagram"),
            ("https://instagram.com/p/ABC123/?igsh=1", "instagram"),
            ("https://www.seriouseats.com/best-chili", None),
        ],
    )
    def test_classify(self, url, platform):
        assert classify_social_url(url) == platform

    def test_profile_urls_are_rejected(self):
        with pytest.raises(SocialExtractError, match="specific TikTok"):
            assert_content_url("https://www.tiktok.com/@chef", "tiktok")
        with pytest.raises(SocialExtractError, match="specific Instagram"):
            assert_content_url("https://www.instagram.com/chef/", "instagram")

    def test_short_tiktok_and_reel_paths_are_content(self):
        assert_content_url("https://vm.tiktok.com/ZMabc123/", "tiktok")
        assert_content_url("https://www.instagram.com/reel/ABC/", "instagram")


class TestSocialMetadataParsing:
    def test_tiktok_oembed_uses_caption_title(self):
        body = json.dumps(
            {
                "title": "Chili noodles: 200g noodles, 2 tbsp chili crisp. Boil, toss.",
                "author_name": "Weeknight Chef",
                "thumbnail_url": "https://cdn.example.com/thumb.jpg",
            }
        ).encode()
        post = parse_oembed_response("tiktok", 200, body)
        assert post.platform == "tiktok"
        assert "chili crisp" in post.caption
        assert post.author_name == "Weeknight Chef"
        assert post.thumbnail_url == "https://cdn.example.com/thumb.jpg"
        block = source_block_for(post)
        assert "Do not invent" in block
        assert "Weeknight Chef" in block

    def test_private_oembed_is_a_fetch_error(self):
        with pytest.raises(SocialExtractError, match="private") as caught:
            parse_oembed_response("tiktok", 403, b"")
        assert caught.value.kind == "fetch"

    def test_empty_caption_is_not_found(self):
        with pytest.raises(SocialExtractError, match="caption") as caught:
            parse_oembed_response("instagram", 200, b'{"title": "  "}')
        assert caught.value.kind == "not_found"

    def test_instagram_login_wall_is_a_fetch_error(self):
        html = "<html><head><title>Login • Instagram</title></head><body>Log in</body></html>"
        with pytest.raises(SocialExtractError, match="didn't share that caption"):
            parse_instagram_html(200, html)

    def test_instagram_og_description_is_the_caption(self):
        html = """
        <html><head>
          <meta property="og:description" content="2 eggs, 1 tbsp butter. Scramble slowly." />
          <meta property="og:image" content="https://cdn.example.com/eggs.jpg" />
        </head></html>
        """
        post = parse_instagram_html(200, html)
        assert "2 eggs" in post.caption
        assert post.thumbnail_url == "https://cdn.example.com/eggs.jpg"


class TestSocialImportPipeline:
    async def test_social_url_reuses_normalizer_and_skips_page_scrape(self):
        service = RecipeImportService.__new__(RecipeImportService)
        request = RecipeImportRequestDTO(
            url="https://www.tiktok.com/@chef/video/123",
            include_source_image=True,
        )
        post = MagicMock(
            platform="tiktok",
            caption="noodles and chili crisp",
            author_name="Chef",
            thumbnail_url="https://cdn.example.com/thumb.jpg",
        )

        with (
            patch.object(RecipeImportService, "_validate_url", return_value=request.url),
            patch(
                "app.services.ai.recipe_import.social.fetch_social_post",
                new=AsyncMock(return_value=post),
            ),
            patch.object(
                service, "_normalize_with_ai", new=AsyncMock(return_value=_recipe())
            ) as normalize,
            patch.object(
                service, "_download_image", new=AsyncMock(return_value="aW1hZ2U=")
            ) as download,
            patch.object(service, "_fetch_html", new=AsyncMock()) as fetch_html,
        ):
            result = await service.import_from_url(request)

        fetch_html.assert_not_called()
        normalize.assert_awaited()
        source = normalize.await_args.args[0]
        assert "noodles and chili crisp" in source
        download.assert_awaited()
        assert result.success is True
        assert result.recipe is not None
        assert result.recipe.recipe_name == "Chili Garlic Noodles"
        assert result.nutrition_facts is None
        assert result.source_url == request.url
        assert result.reference_image_data == "aW1hZ2U="

    async def test_private_post_is_a_fetch_error(self):
        service = RecipeImportService.__new__(RecipeImportService)
        request = RecipeImportRequestDTO(url="https://www.instagram.com/reel/ABC/")
        with (
            patch.object(RecipeImportService, "_validate_url", return_value=request.url),
            patch(
                "app.services.ai.recipe_import.social.fetch_social_post",
                new=AsyncMock(side_effect=SocialExtractError("That Instagram post is private.", "fetch")),
            ),
        ):
            with pytest.raises(RecipeImportFetchError, match="private"):
                await service.import_from_url(request)

    async def test_caption_without_a_recipe_is_not_found(self):
        service = RecipeImportService.__new__(RecipeImportService)
        request = RecipeImportRequestDTO(url="https://www.tiktok.com/@chef/video/9")
        post = MagicMock(platform="tiktok", caption="lol", author_name=None, thumbnail_url=None)
        with (
            patch.object(RecipeImportService, "_validate_url", return_value=request.url),
            patch(
                "app.services.ai.recipe_import.social.fetch_social_post",
                new=AsyncMock(return_value=post),
            ),
            patch.object(
                service,
                "_normalize_with_ai",
                new=AsyncMock(
                    side_effect=RecipeImportNotFoundError("No recipe was found on that page.")
                ),
            ),
        ):
            with pytest.raises(RecipeImportNotFoundError, match="out loud"):
                await service.import_from_url(request)
