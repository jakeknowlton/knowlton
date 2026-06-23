"""Aggregates the routers for the Food section's subsections.

Section names are intentionally kept out of the URL paths, so this router adds
no prefix of its own — it simply collects the subsection routers (recipes today,
more later) under one include for `main` to mount. Mirrors `home/router.py`.
"""

from fastapi import APIRouter

from food.recipes.router import router as recipes_router

router = APIRouter()
router.include_router(recipes_router)
