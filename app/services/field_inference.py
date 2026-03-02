"""Infer ClickUp custom field values from task name and context hints."""

import re

from app.models.clickup import FieldOption, InferredFields
from app.services.clickup_fields import clickup_fields


# Revenue mapping: project name → revenue level
_REVENUE_MAP = {
    "Dalton Law": "Direct, High",
    "Devon Ervin": "Direct, High",
    "Lingua Ink Media": "Direct, High",
    "Lynn Haller": "Direct, Low",
    "Carolyn Martin": "Direct, Low",
    "Daniela Morescalchi": "Direct, Low",
    "Tomahawk Destiny": "Direct, Low",
    "Lingua Ink Books": "Indirect",
    "Lingua Ink Courses": "Indirect",
    "Lingua Ink Cohorts": "Indirect",
    "Maya Bairey": "Indirect",
    "Job Search": "Indirect",
    "Sulima Malzin": "None",
    "Free Cohort": "None",
    "Raging Grannies": "None",
    "Personal": "None",
}

# Internal-scope projects
_INTERNAL_PROJECTS = {
    "Lingua Ink Books", "Lingua Ink Media", "Lingua Ink Courses",
    "Lingua Ink Cohorts", "Maya Bairey", "Personal", "Job Search",
}

# Effort keyword patterns
_EFFORT_PATTERNS = [
    (r"\b(reply|respond|email|forward|send)\b", "Tiny"),
    (r"\b(write|draft|compose|outline|edit|copyedit)\b", "Medium"),
    (r"\b(launch|rebuild|redesign|migrate|overhaul|build)\b", "Big"),
]

# Readiness keyword patterns
_READINESS_PATTERNS = [
    (r"\b(learn|research|figure out|look into|investigate|study|explore)\b", "Upskilling"),
]


def infer_fields(task_name: str, description: str = "") -> InferredFields:
    """Infer custom field values from task name and description.

    Approach is NEVER inferred — always left None.
    """
    text = f"{task_name} {description}".lower()
    result = InferredFields()

    # --- Project inference ---
    keyword_index = clickup_fields.project_keyword_index()
    best_match: FieldOption | None = None
    best_len = 0

    # Try multi-word matches first (longer = more specific)
    for keyword, option in sorted(keyword_index.items(), key=lambda x: -len(x[0])):
        # Match keyword, allowing possessive forms (devon's, devons)
        pattern = r"\b" + re.escape(keyword.lower()) + r"(?:'?s)?\b"
        if re.search(pattern, text):
            if len(keyword) > best_len:
                best_match = option
                best_len = len(keyword)

    if best_match:
        result.project = best_match
        result.project_confident = best_len > 3  # short matches are less confident

    # --- Revenue inference (from project) ---
    if result.project:
        rev_name = _REVENUE_MAP.get(result.project.name)
        if rev_name:
            result.revenue = clickup_fields.option_by_name("Revenue", rev_name)

    # Default revenue if no project match
    if not result.revenue:
        result.revenue = clickup_fields.option_by_name("Revenue", "None")

    # --- Scope inference (from project) ---
    if result.project and result.project.name in _INTERNAL_PROJECTS:
        result.scope = clickup_fields.option_by_name("Scope", "Internal")
    else:
        result.scope = clickup_fields.option_by_name("Scope", "External")

    # --- Effort inference (from keywords) ---
    effort_name = "Small"  # default
    for pattern, level in _EFFORT_PATTERNS:
        if re.search(pattern, text):
            effort_name = level
            break
    result.effort = clickup_fields.option_by_name("Effort", effort_name)

    # --- Readiness inference ---
    readiness_name = "Prepared"  # default
    for pattern, level in _READINESS_PATTERNS:
        if re.search(pattern, text):
            readiness_name = level
            break
    result.readiness = clickup_fields.option_by_name("Readiness", readiness_name)

    # --- Approach: NEVER inferred ---
    result.approach = None

    return result
