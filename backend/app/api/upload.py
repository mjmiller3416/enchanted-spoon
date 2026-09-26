"""Upload API endpoints for image handling via Cloudinary.

All endpoints require authentication to prevent unauthorized uploads.

Images are addressed in Cloudinary by the recipe's stable ``image_key`` (not its
mutable primary key), so URLs stay valid across environments (local SQLite vs
prod Postgres) and never collide with a different recipe's id. The key is
resolved server-side from the recipe the caller owns, which also enforces that
a user can only upload images for their own recipes.
"""

import os
import base64
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

from app.api.auth import get_current_user
from app.database.db import get_session
from app.models.user import User
from app.services.recipe_service import RecipeService

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

router = APIRouter()


def _resolve_image_key(session: Session, user: User, recipe_id_raw: str) -> str:
    """Resolve the stable Cloudinary image_key for a recipe owned by the caller.

    Args:
        session: Active database session.
        user: The authenticated user.
        recipe_id_raw: The recipe id from the form (string).

    Returns:
        The recipe's image_key.

    Raises:
        HTTPException 400: recipeId is not an integer.
        HTTPException 404: recipe does not exist or is not owned by the user.
    """
    try:
        recipe_id = int(recipe_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="recipeId must be an integer")

    recipe = RecipeService(session, user.id).get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe.image_key


@router.post("")
async def upload_recipe_image(
    file: UploadFile = File(...),
    recipeId: str = Form(...),
    imageType: str = Form(default="reference"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Upload a recipe image to Cloudinary.

    Args:
        file: The image file to upload
        recipeId: The recipe ID (used to resolve the recipe's stable image_key)
        imageType: Either "reference" (thumbnail) or "banner" (hero image)

    Returns:
        success: Whether upload succeeded
        path: The Cloudinary URL for the image
        filename: The public ID of the uploaded image
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Validate imageType
    if imageType not in ("reference", "banner"):
        imageType = "reference"

    image_key = _resolve_image_key(session, current_user, recipeId)

    try:
        # Read file contents
        contents = await file.read()

        # Upload to Cloudinary keyed by the recipe's stable image_key
        result = cloudinary.uploader.upload(
            contents,
            folder=f"meal-genie/recipes/{image_key}",
            public_id=f"{imageType}_{image_key}",
            overwrite=True,
            resource_type="image",
        )

        return {
            "success": True,
            "path": result["secure_url"],
            "filename": result["public_id"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/base64")
async def upload_base64_image(
    image_data: str = Form(...),
    recipeId: str = Form(...),
    imageType: str = Form(default="reference"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Upload a base64 encoded image to Cloudinary.

    Used for AI-generated images that come as base64 strings.

    Args:
        image_data: Base64 encoded image data
        recipeId: The recipe ID (used to resolve the recipe's stable image_key)
        imageType: Either "reference" (thumbnail) or "banner" (hero image)

    Returns:
        success: Whether upload succeeded
        path: The Cloudinary URL for the image
        filename: The public ID of the uploaded image
    """
    # Validate imageType
    if imageType not in ("reference", "banner"):
        imageType = "reference"

    image_key = _resolve_image_key(session, current_user, recipeId)

    try:
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_data)

        # Upload to Cloudinary keyed by the recipe's stable image_key
        result = cloudinary.uploader.upload(
            image_bytes,
            folder=f"meal-genie/recipes/{image_key}",
            public_id=f"{imageType}_{image_key}",
            overwrite=True,
            resource_type="image",
        )

        return {
            "success": True,
            "path": result["secure_url"],
            "filename": result["public_id"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
