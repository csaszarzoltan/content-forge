"""Languages endpoint — GET /api/v1/languages.

Public endpoint that returns the list of supported languages.
No authentication required — used by frontend for language picker.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Response

from src.schemas.languages import LanguageResponse
from src.services.language_data import LanguageDataService

router = APIRouter(prefix="/api/v1/languages", tags=["languages"])

# Singleton service instance — static data, no DB dependency
_language_service = LanguageDataService()


@router.get("", response_model=LanguageResponse)
async def get_languages(response: Response) -> LanguageResponse:
    """Return all supported languages with status and metadata.

    Response is cacheable — includes Cache-Control and ETag headers.
    No authentication required.

    Args:
        response: FastAPI Response object for setting cache headers.

    Returns:
        LanguageResponse with languages list and total count.
    """
    result = _language_service.get_languages()

    # Generate ETag from content hash for caching
    data_json = result.model_dump_json()
    etag = hashlib.md5(data_json.encode("utf-8")).hexdigest()

    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["ETag"] = f'"{etag}"'

    return result
