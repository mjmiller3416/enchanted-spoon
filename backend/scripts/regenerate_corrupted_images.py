#!/usr/bin/env python3
"""
One-time repair for the 10 recipe rows whose Cloudinary images were clobbered
before the stable image_key fix (issues #131, #184).

Background
----------
Pre-fix, assets were keyed by DB primary key in a Cloudinary account shared
between local dev and prod, so a local recipe with the same id could overwrite
a prod recipe's photo. The Aug 2026 remediation (`remediate_recipe_image_keys.py`)
isolated every asset onto its own image_key path, but by design it froze each
recipe's *current* image — including the five that had already been clobbered.
Cross-environment clobbers are invisible to any same-DB collision scan, so these
five were only findable by visually auditing every image against its recipe name
(done 2026-08-20; see issue #184). The originals were overwritten in Cloudinary
and are unrecoverable, so this script regenerates them.

Affected rows (verified visually — each shows the local dev recipe that shared
its pre-fix id):

    dish                                 user 1   user 3   photo showed
    Tuscan Chicken Pasta (+banner)        124      302     baked beans
    Caprese Chicken Skillet               131      309     fish sandwiches
    Tilapia Fish Tacos                    164      340     chicken avocado salad
    Simple Street Corn                    165      341     creamy shells & cheese
    Noodles with Garlicky Cream Sauce     166      342     chicken tenders

What this script does
---------------------
Phase 1 (--generate): generates replacement images via the app's Gemini image
service, using each user's own custom image prompt from their settings so the
new photos match the rest of their catalog. Images are written to a local
review directory — nothing touches Cloudinary or the database. Re-running
skips images that already exist, so failed generations can be retried and
unwanted results can be deleted and regenerated.

Phase 2 (--apply): uploads the reviewed images to each recipe's canonical
Cloudinary path (meal-genie/recipes/{image_key}/{type}_{image_key}) and
updates the row's image URL.

Usage
-----
    # Requires GEMINI_IMAGE_API_KEY + CLOUDINARY_* in backend/.env
    python scripts/regenerate_corrupted_images.py --database-url "postgresql://..." --generate
    # ... review the images in scripts/regen_review/ ...
    python scripts/regenerate_corrupted_images.py --database-url "postgresql://..." --apply
"""

import argparse
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).parent.parent / ".env")

REVIEW_DIR = Path(__file__).parent / "regen_review"

# dish -> affected rows. `banner` marks rows whose banner asset was also clobbered.
TARGETS = [
    {"dish": "Tuscan Chicken Pasta",
     "rows": [{"id": 124, "user_id": 1, "banner": True},
              {"id": 302, "user_id": 3, "banner": True}]},
    {"dish": "Caprese Chicken Skillet",
     "rows": [{"id": 131, "user_id": 1, "banner": False},
              {"id": 309, "user_id": 3, "banner": False}]},
    {"dish": "Tilapia Fish Tacos",
     "rows": [{"id": 164, "user_id": 1, "banner": False},
              {"id": 340, "user_id": 3, "banner": False}]},
    {"dish": "Simple Street Corn",
     "rows": [{"id": 165, "user_id": 1, "banner": False},
              {"id": 341, "user_id": 3, "banner": False}]},
    {"dish": "Noodles with Garlicky Cream Sauce",
     "rows": [{"id": 166, "user_id": 1, "banner": False},
              {"id": 342, "user_id": 3, "banner": False}]},
]


def create_db_session(database_url: str):
    engine = create_engine(database_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def load_user_prompts(session) -> dict[int, str | None]:
    """Fetch each affected user's custom image prompt so regenerated photos match their catalog."""
    prompts: dict[int, str | None] = {}
    rows = session.execute(
        text("SELECT user_id, settings_json FROM user_settings WHERE user_id IN (1, 3)")
    ).mappings().all()
    for row in rows:
        settings = row["settings_json"]
        if not isinstance(settings, dict):
            settings = json.loads(settings or "{}")
        prompts[row["user_id"]] = settings.get("aiFeatures", {}).get("imageGenerationPrompt")
    return prompts


def verify_rows(session) -> dict[int, dict]:
    """Confirm every target row still exists with the expected dish name and return id -> row."""
    ids = [r["id"] for t in TARGETS for r in t["rows"]]
    rows = {
        r["id"]: r
        for r in session.execute(
            text("SELECT id, user_id, recipe_name, image_key FROM recipe WHERE id = ANY(:ids)"),
            {"ids": ids},
        ).mappings().all()
    }
    for target in TARGETS:
        for spec in target["rows"]:
            row = rows.get(spec["id"])
            if row is None:
                sys.exit(f"ABORT: recipe {spec['id']} not found in this database.")
            if row["recipe_name"].strip().lower() != target["dish"].strip().lower():
                sys.exit(
                    f"ABORT: recipe {spec['id']} is {row['recipe_name']!r}, expected "
                    f"{target['dish']!r} — wrong database?"
                )
            if row["user_id"] != spec["user_id"]:
                sys.exit(f"ABORT: recipe {spec['id']} belongs to user {row['user_id']}, "
                         f"expected {spec['user_id']}.")
    return rows


async def generate(session) -> None:
    """Phase 1: generate replacement images into REVIEW_DIR. No prod writes."""
    from app.services.ai.image_generation.service import get_image_generation_service

    rows = verify_rows(session)
    prompts = load_user_prompts(session)
    service = get_image_generation_service()
    REVIEW_DIR.mkdir(exist_ok=True)

    failures = 0
    for target in TARGETS:
        for spec in target["rows"]:
            # Review files use the same naming as the Cloudinary assets:
            # {imageType}_{image_key}.jpg
            image_key = rows[spec["id"]]["image_key"]
            ref_path = REVIEW_DIR / f"reference_{image_key}.jpg"
            if ref_path.exists():
                print(f"  [SKIP] {ref_path.name} already exists")
            else:
                print(f"  [GEN]  recipe {spec['id']} ({target['dish']}, user {spec['user_id']}) reference...")
                result = await service.generate_recipe_image(
                    target["dish"],
                    custom_prompt=prompts.get(spec["user_id"]),
                    aspect_ratio="1:1",
                    image_size="2K",
                )
                if not result["success"]:
                    print(f"  [FAIL] {result['error']}")
                    failures += 1
                    continue
                ref_path.write_bytes(base64.b64decode(result["image_data"]))
                print(f"         -> {ref_path.name}")

            if spec["banner"]:
                banner_path = REVIEW_DIR / f"banner_{image_key}.jpg"
                if banner_path.exists():
                    print(f"  [SKIP] {banner_path.name} already exists")
                    continue
                print(f"  [GEN]  recipe {spec['id']} banner (from reference)...")
                result = await service.generate_banner_from_reference(
                    target["dish"], ref_path.read_bytes()
                )
                if not result["success"]:
                    print(f"  [FAIL] {result['error']}")
                    failures += 1
                    continue
                banner_path.write_bytes(base64.b64decode(result["image_data"]))
                print(f"         -> {banner_path.name}")

    print(f"\nDone. {failures} failure(s). Review the images in {REVIEW_DIR}")
    print("Delete any you don't like and re-run --generate, then run --apply.")


def apply(session) -> None:
    """Phase 2: upload reviewed images to canonical Cloudinary paths and update the rows."""
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

    rows = verify_rows(session)

    # Every expected image must exist before any write happens.
    missing = []
    for target in TARGETS:
        for spec in target["rows"]:
            image_key = rows[spec["id"]]["image_key"]
            if not (REVIEW_DIR / f"reference_{image_key}.jpg").exists():
                missing.append(f"reference_{image_key}.jpg (recipe {spec['id']})")
            if spec["banner"] and not (REVIEW_DIR / f"banner_{image_key}.jpg").exists():
                missing.append(f"banner_{image_key}.jpg (recipe {spec['id']})")
    if missing:
        sys.exit(f"ABORT: missing review images (run --generate first): {missing}")

    field_for = {"reference": "reference_image_path", "banner": "banner_image_path"}
    for target in TARGETS:
        for spec in target["rows"]:
            image_key = rows[spec["id"]]["image_key"]
            image_types = ["reference"] + (["banner"] if spec["banner"] else [])
            for image_type in image_types:
                image_bytes = (REVIEW_DIR / f"{image_type}_{image_key}.jpg").read_bytes()
                result = cloudinary.uploader.upload(
                    image_bytes,
                    folder=f"meal-genie/recipes/{image_key}",
                    public_id=f"{image_type}_{image_key}",
                    overwrite=True,
                    resource_type="image",
                )
                new_url = result["secure_url"]
                session.execute(
                    text(f"UPDATE recipe SET {field_for[image_type]} = :url WHERE id = :id"),
                    {"url": new_url, "id": spec["id"]},
                )
                print(f"  [FIXED] recipe {spec['id']} ({target['dish']}) {image_type} -> {new_url}")

    session.commit()
    print("\nAll rows updated and committed.")


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate the recipe images clobbered before the image_key fix.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--database-url", type=str, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate", action="store_true",
                      help="Generate replacement images into scripts/regen_review/ (no writes)")
    mode.add_argument("--apply", action="store_true",
                      help="Upload reviewed images to Cloudinary and update the rows")
    args = parser.parse_args()

    session = create_db_session(args.database_url)
    try:
        if args.generate:
            asyncio.run(generate(session))
        else:
            apply(session)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
