#!/usr/bin/env python3
"""
Generate artwork for the onboarding starter pack with the app's standard
Gemini image workflow, then publish it for every new account to share.

Phase 1 (--generate): for each starter recipe, generates a 1:1 reference
image and a banner derived from it (the same two-step flow the recipe wizard
uses) into scripts/starter_review/. Nothing is uploaded. Re-running skips
images that already exist, so delete any you don't like and run it again.

Phase 2 (--apply): uploads the reviewed images to a shared Cloudinary folder
(meal-genie/starter-pack/{slug}/) and writes their URLs to
app/services/sample_data/starter_images.json, which the starter pack reads.
Commit that JSON file; accounts seeded after it deploys get the images.
Existing sample recipes keep the image they were seeded with.

Usage
-----
    # Requires GEMINI_IMAGE_API_KEY (+ CLOUDINARY_* for --apply) in backend/.env
    python scripts/generate_starter_images.py --generate
    # ... review scripts/starter_review/ ...
    python scripts/generate_starter_images.py --apply
    # Optional: match a house style (template must include {recipe_name})
    python scripts/generate_starter_images.py --generate --prompt "..."
"""

import argparse
import asyncio
import base64
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from app.services.sample_data.starter_pack import IMAGE_MANIFEST_PATH, STARTER_RECIPES

REVIEW_DIR = Path(__file__).parent / "starter_review"
CLOUDINARY_FOLDER = "meal-genie/starter-pack"
# Each image usually takes 20-60s; anything past this is treated as a hang
GENERATION_TIMEOUT_SECONDS = 180


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


async def timed(label: str, call) -> dict:
    """Await an image call with a timeout, printing how long it took."""
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(call, GENERATION_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        result = {"success": False, "error": f"timed out after {GENERATION_TIMEOUT_SECONDS}s"}
    print(f"         ({label}: {time.monotonic() - started:.0f}s)")
    return result


def review_path(recipe_name: str, image_type: str) -> Path:
    return REVIEW_DIR / f"{image_type}_{slugify(recipe_name)}.jpg"


async def generate(custom_prompt: str | None) -> None:
    """Phase 1: generate reference + banner images into REVIEW_DIR. No uploads."""
    from app.services.ai.image_generation.service import get_image_generation_service

    if not os.getenv("GEMINI_IMAGE_API_KEY"):
        sys.exit("ERROR: --generate requires GEMINI_IMAGE_API_KEY in env.")

    service = get_image_generation_service()
    REVIEW_DIR.mkdir(exist_ok=True)

    failures = 0
    for recipe in STARTER_RECIPES:
        name = recipe["recipe_name"]
        ref_path = review_path(name, "reference")
        if ref_path.exists():
            print(f"  [SKIP] {ref_path.name} already exists")
        else:
            print(f"  [GEN]  {name} reference (usually 20-60s)...", flush=True)
            result = await timed("reference", service.generate_recipe_image(
                name, custom_prompt=custom_prompt, aspect_ratio="1:1", image_size="2K"
            ))
            if not result["success"]:
                print(f"  [FAIL] {result['error']}")
                failures += 1
                continue
            ref_path.write_bytes(base64.b64decode(result["image_data"]))
            print(f"         -> {ref_path.name}")

        banner_path = review_path(name, "banner")
        if banner_path.exists():
            print(f"  [SKIP] {banner_path.name} already exists")
            continue
        print(f"  [GEN]  {name} banner (from reference)...", flush=True)
        result = await timed(
            "banner", service.generate_banner_from_reference(name, ref_path.read_bytes())
        )
        if not result["success"]:
            print(f"  [FAIL] {result['error']}")
            failures += 1
            continue
        banner_path.write_bytes(base64.b64decode(result["image_data"]))
        print(f"         -> {banner_path.name}")

    print(f"\nDone. {failures} failure(s). Review the images in {REVIEW_DIR}")
    print("Delete any you don't like and re-run --generate, then run --apply.")


def apply() -> None:
    """Phase 2: upload reviewed images to Cloudinary and write the URL manifest."""
    import cloudinary
    import cloudinary.uploader

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    if not cloud_name:
        sys.exit("ERROR: --apply requires CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET in env.")
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )

    # Every image must exist before anything is uploaded.
    missing = [
        path.name
        for recipe in STARTER_RECIPES
        for path in (review_path(recipe["recipe_name"], "reference"),
                     review_path(recipe["recipe_name"], "banner"))
        if not path.exists()
    ]
    if missing:
        sys.exit(f"ABORT: missing review images (run --generate first): {missing}")

    manifest: dict[str, dict[str, str]] = {}
    for recipe in STARTER_RECIPES:
        name = recipe["recipe_name"]
        slug = slugify(name)
        manifest[name] = {}
        for image_type in ("reference", "banner"):
            result = cloudinary.uploader.upload(
                review_path(name, image_type).read_bytes(),
                folder=f"{CLOUDINARY_FOLDER}/{slug}",
                public_id=f"{image_type}_{slug}",
                overwrite=True,
                resource_type="image",
            )
            manifest[name][image_type] = result["secure_url"]
            print(f"  [UP] {name} {image_type} -> {result['secure_url']}")

    IMAGE_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nWrote {IMAGE_MANIFEST_PATH}. Commit it to ship the images.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and publish onboarding starter-pack images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate", action="store_true",
                      help="Generate images into scripts/starter_review/ (no uploads)")
    mode.add_argument("--apply", action="store_true",
                      help="Upload reviewed images to Cloudinary and write starter_images.json")
    parser.add_argument("--prompt", type=str, default=None,
                        help="Custom image prompt template (must include {recipe_name})")
    args = parser.parse_args()

    if args.generate:
        asyncio.run(generate(args.prompt))
    else:
        apply()


if __name__ == "__main__":
    main()
