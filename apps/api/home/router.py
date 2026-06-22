"""Aggregates the routers for the Home section's subsections.

Section names are intentionally kept out of the URL paths, so this router adds
no prefix of its own — it simply collects the subsection routers (laundry today,
more later) under one include for `main` to mount.
"""

from fastapi import APIRouter

from home.laundry.router import router as laundry_router

router = APIRouter()
router.include_router(laundry_router)
