"""app/api/conversion_rules.py

FastAPI router for unit conversion rule endpoints.
All endpoints require authentication and are scoped to the current user.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.unit_conversion_dtos import (
    UnitConversionRuleCreateDTO,
    UnitConversionRuleResponseDTO,
    UnitConversionRuleUpdateDTO,
    UnitOptionDTO,
    UnitsResponseDTO,
)
from app.models.user import User
from app.services.unit_conversion_service import (
    ConversionRuleNotFoundError,
    UnitConversionService,
)
from app.utils.unit_conversion import MASS_UNITS, VOLUME_UNITS, COUNT_UNITS

router = APIRouter()


def _rule_to_response_dto(rule) -> UnitConversionRuleResponseDTO:
    """Convert a UnitConversionRule model to response DTO."""
    return UnitConversionRuleResponseDTO(
        id=rule.id,
        ingredient_name=rule.ingredient_name,
        from_unit=rule.from_unit,
        to_unit=rule.to_unit,
        factor=rule.factor,
        round_up=rule.round_up,
        created_at=rule.created_at,
    )


def _get_unit_label(value: str) -> str:
    """Get display label for a unit value."""
    # Map of unit values to their display labels
    # This matches the labels used in frontend/src/lib/constants.ts
    label_map = {
        "tbs": "Tbs",
        "tsp": "tsp",
        "cup": "cup",
        "oz": "oz",
        "lbs": "lbs",
        "stick": "stick",
        "bag": "bag",
        "box": "box",
        "can": "can",
        "jar": "jar",
        "package": "package",
        "piece": "piece",
        "slice": "slice",
        "whole": "whole",
        "pinch": "pinch",
        "dash": "dash",
        "to-taste": "to taste",
    }
    return label_map.get(value, value)


@router.get("/units", response_model=UnitsResponseDTO)
async def get_units(
    current_user: User = Depends(get_current_user),
):
    """
    Get all available ingredient units.

    Returns a list of unit options with their values and display labels.
    This endpoint serves as the single source of truth for allowed units,
    eliminating the need to maintain duplicate unit lists in the frontend.
    """
    # Combine all unit types
    all_units = set()
    all_units.update(MASS_UNITS.keys())
    all_units.update(VOLUME_UNITS.keys())
    all_units.update(COUNT_UNITS)

    # Remove empty string (it's internal-only for "no unit")
    all_units.discard("")

    # Convert to list of UnitOptionDTO
    units = [
        UnitOptionDTO(value=unit, label=_get_unit_label(unit))
        for unit in sorted(all_units)
    ]

    return UnitsResponseDTO(units=units)


@router.get("", response_model=List[UnitConversionRuleResponseDTO])
async def list_rules(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all unit conversion rules for the current user."""
    service = UnitConversionService(session, current_user.id)
    rules = service.get_all()
    return [_rule_to_response_dto(r) for r in rules]


@router.get("/{rule_id}", response_model=UnitConversionRuleResponseDTO)
async def get_rule(
    rule_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a single rule by ID."""
    service = UnitConversionService(session, current_user.id)
    rule = service.get_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _rule_to_response_dto(rule)


@router.post("", response_model=UnitConversionRuleResponseDTO, status_code=201)
async def create_rule(
    rule_data: UnitConversionRuleCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new unit conversion rule."""
    service = UnitConversionService(session, current_user.id)
    try:
        rule = service.create_rule(rule_data)
        return _rule_to_response_dto(rule)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{rule_id}", response_model=UnitConversionRuleResponseDTO)
async def update_rule(
    rule_id: int,
    update_data: UnitConversionRuleUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update an existing rule."""
    service = UnitConversionService(session, current_user.id)
    try:
        rule = service.update_rule(rule_id, update_data)
        return _rule_to_response_dto(rule)
    except ConversionRuleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a rule by ID."""
    service = UnitConversionService(session, current_user.id)
    try:
        service.delete_rule(rule_id)
        return {"message": "Rule deleted successfully"}
    except ConversionRuleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
