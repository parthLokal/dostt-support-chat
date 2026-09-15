from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import issue_admin_token
from app.db.session import get_db
from app.schemas.admin import AdminLoginRequest, AdminLoginResponse
from app.services import auth_service

router = APIRouter(prefix="/api/admin/login", tags=["admin"])


@router.post("", response_model=AdminLoginResponse)
def login(payload: AdminLoginRequest, db: Session = Depends(get_db)) -> AdminLoginResponse:
    admin = auth_service.login(db, payload.email, payload.password)
    token = issue_admin_token(admin.id)
    return AdminLoginResponse(token=token, name=admin.name, email=admin.email)
