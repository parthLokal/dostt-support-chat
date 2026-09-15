"""Builds an authenticated Gemini client against Vertex AI — a GCP service
account, not a bare Gemini API key, per the org's Vertex AI migration guide
(also followed by the AstroHelp sibling project): production shouldn't use a
bare API key, and billing needs to be attributable per request via the
`labels` each call site passes into GenerateContentConfig.
"""

from google import genai
from google.oauth2 import service_account

from app.core.config import settings
from app.core.google_credentials import parse_service_account_json

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def build_vertex_client() -> genai.Client:
    info = parse_service_account_json(settings.GEMINI_VERTEX_CREDENTIALS_JSON)
    if info is None:
        raise RuntimeError(
            "GEMINI_VERTEX_CREDENTIALS_JSON is not set — required for the chat agent to reach "
            "Gemini via Vertex AI."
        )
    credentials = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
    return genai.Client(
        vertexai=True,
        project=info["project_id"],
        location=settings.GOOGLE_CLOUD_LOCATION,
        credentials=credentials,
    )


def billing_labels() -> dict[str, str]:
    return {"billing_category": f"{settings.ENVIRONMENT}_{settings.GEMINI_BILLING_FEATURE}"}
