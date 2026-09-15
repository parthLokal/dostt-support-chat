from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations import call_client
from app.schemas.chat import CallOut

router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.get("", response_model=list[CallOut])
def list_recent_calls(account_id: int = Query(...), db: Session = Depends(get_db)) -> list[CallOut]:
    calls = call_client.get_recent_calls(db, account_id)
    return [CallOut.model_validate(c, from_attributes=True) for c in calls]
