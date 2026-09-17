from functools import lru_cache

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from backend.config import settings


@lru_cache(maxsize=1)
def get_search_client() -> SearchClient:
    if not settings.AZURE_SEARCH_ENDPOINT:
        raise RuntimeError("AZURE_SEARCH_ENDPOINT is not configured.")

    if not settings.AZURE_SEARCH_KEY:
        raise RuntimeError("AZURE_SEARCH_KEY is not configured.")

    if not settings.AZURE_SEARCH_INDEX:
        raise RuntimeError("AZURE_SEARCH_INDEX is not configured.")

    return SearchClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        index_name=settings.AZURE_SEARCH_INDEX,
        credential=AzureKeyCredential(
            settings.AZURE_SEARCH_KEY
        ),
    )