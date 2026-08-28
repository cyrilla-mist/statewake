from enum import StrEnum

from pydantic import BaseModel


class OverallValidity(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    AMBIGUOUS = "AMBIGUOUS"


class ValidityResult(BaseModel):
    overall_validity: OverallValidity
    previous_next_action_valid: bool
    direction_conflict: bool
    clarification_required: bool