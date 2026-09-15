"""Already structured as a real Slack incoming-webhook call — under
SLACK_MOCK_MODE it skips the network call and writes a row to `slack_log`
instead (what the admin dashboard's Slack Log page reads). To go live: set
SLACK_MOCK_MODE=false and SLACK_WEBHOOK_URL to a real incoming webhook.
"""

import logging

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.slack_log import SlackLog

logger = logging.getLogger(__name__)


def notify_ticket_created(db: Session, *, ticket_id: int, message: str) -> None:
    channel = settings.SLACK_SUPPORT_CHANNEL

    if settings.SLACK_MOCK_MODE:
        db.add(SlackLog(channel=channel, message=message, ticket_id=ticket_id))
        return

    try:
        httpx.post(settings.SLACK_WEBHOOK_URL, json={"text": message}, timeout=5.0)
    except httpx.HTTPError:
        logger.exception("Slack notification failed for ticket %s", ticket_id)
    db.add(SlackLog(channel=channel, message=message, ticket_id=ticket_id))
