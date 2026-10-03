"""NGO / Responder user registration, login, and incident management API."""
from __future__ import annotations

import datetime as dt
import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.database import get_db
from app.models.detection import Detection
from app.models.other import RiskAssessment
from app.models.user import IncidentAction, User

logger = logging.getLogger("ghostnet.api.users")

router = APIRouter(prefix="/api/v1/users", tags=["users"])
_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=8)
    full_name: str
    organization: str = ""
    role: str = "responder"  # ngo, responder, researcher, coast_guard, admin
    phone: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class IncidentUpdateRequest(BaseModel):
    action: str  # verify, reject, assign, being_handled, resolve
    assigned_team: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
    user = db.query(User).filter(User.id == payload.get("sub")).one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")
    return user


# ---------------------------------------------------------------------------
# Registration & Login
# ---------------------------------------------------------------------------


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    existing = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    allowed_roles = {"ngo", "responder", "researcher", "coast_guard", "admin"}
    if payload.role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"role must be one of {allowed_roles}")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        organization=payload.organization,
        role=payload.role,
        phone=payload.phone,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("[AUTH] Registered user %s (%s)", user.email, user.role)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "organization": user.organization,
        "role": user.role,
        "message": "Registration successful. You can now log in.",
    }


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "organization": user.organization,
            "role": user.role,
        },
    )


@router.get("/me")
def get_me(current_user: User = Depends(_get_current_user)) -> dict:
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "organization": current_user.organization,
        "role": current_user.role,
        "phone": current_user.phone,
        "created_at": current_user.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Alert inbox — detections awaiting verification or action
# ---------------------------------------------------------------------------


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db), current_user: User = Depends(_get_current_user)) -> dict:
    """
    Returns two lists:
    - verification_queue: confidence < 0.70, status=unverified (need human review)
    - actionable_alerts: confidence >= 0.70, unverified/verified (high-confidence, ready for cleanup)
    All include latest risk/drift info if analyzed.
    """
    detections = db.query(Detection).order_by(Detection.timestamp.desc()).limit(200).all()
    risk_by_det = {
        r.detection_id: r
        for r in db.query(RiskAssessment).all()
    }

    verification_queue = []
    actionable_alerts = []

    for d in detections:
        risk = risk_by_det.get(d.id)
        record = {
            "id": d.id,
            "external_id": d.external_id,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "confidence": d.confidence,
            "object_class": d.object_class,
            "status": d.incident_status or d.status,
            "timestamp": d.timestamp.isoformat(),
            "source": d.source,
            "assigned_to": d.assigned_to,
            "assigned_team": d.assigned_team,
            "verification_notes": d.verification_notes,
            "verified_by": d.verified_by,
            "risk_score": risk.risk_score if risk else None,
            "risk_level": risk.risk_level if risk else None,
            "priority_level": risk.priority_level if risk else None,
            "recommended_action": risk.recommended_action if risk else None,
        }
        if d.confidence >= 0.70:
            actionable_alerts.append(record)
        elif d.incident_status not in ("resolved", "rejected"):
            verification_queue.append(record)

    return {
        "verification_queue": verification_queue,
        "actionable_alerts": actionable_alerts,
        "total_requiring_action": len(verification_queue),
        "total_actionable": len(actionable_alerts),
    }


# ---------------------------------------------------------------------------
# Incident management — update status
# ---------------------------------------------------------------------------


@router.post("/incidents/{detection_id}/update")
def update_incident(
    detection_id: str,
    payload: IncidentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
) -> dict:
    """
    Allows responders to verify, reject, assign, mark being_handled, or resolve an incident.
    """
    detection = (
        db.query(Detection)
        .filter((Detection.id == detection_id) | (Detection.external_id == detection_id))
        .one_or_none()
    )
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")

    action = payload.action.lower()
    allowed_actions = {"verify", "reject", "assign", "being_handled", "resolve"}
    if action not in allowed_actions:
        raise HTTPException(status_code=400, detail=f"action must be one of {allowed_actions}")

    status_map = {
        "verify": "verified",
        "reject": "rejected",
        "assign": "assigned",
        "being_handled": "being_handled",
        "resolve": "resolved",
    }
    old_status = detection.incident_status or detection.status
    new_status = status_map[action]

    detection.incident_status = new_status
    detection.status = new_status
    if action == "verify":
        detection.verified_by = current_user.full_name
        detection.verified_at = dt.datetime.utcnow()
    if payload.assigned_team:
        detection.assigned_team = payload.assigned_team
        detection.assigned_to = current_user.full_name
    if payload.notes:
        detection.verification_notes = payload.notes

    incident_action = IncidentAction(
        detection_id=detection.id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        organization=current_user.organization,
        action=action,
        previous_status=old_status,
        new_status=new_status,
        assigned_team=payload.assigned_team,
        notes=payload.notes,
    )
    db.add(incident_action)
    db.commit()
    db.refresh(detection)

    logger.info(
        "[INCIDENT] %s -> %s | detection=%s | user=%s",
        old_status, new_status, detection.external_id, current_user.email,
    )
    return {
        "detection_id": detection.external_id,
        "old_status": old_status,
        "new_status": new_status,
        "updated_by": current_user.full_name,
        "organization": current_user.organization,
        "notes": payload.notes,
    }


@router.get("/incidents/{detection_id}/history")
def get_incident_history(
    detection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
) -> dict:
    detection = (
        db.query(Detection)
        .filter((Detection.id == detection_id) | (Detection.external_id == detection_id))
        .one_or_none()
    )
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")

    actions = (
        db.query(IncidentAction)
        .filter(IncidentAction.detection_id == detection.id)
        .order_by(IncidentAction.created_at)
        .all()
    )
    return {
        "detection_id": detection.external_id,
        "current_status": detection.incident_status or detection.status,
        "actions": [
            {
                "id": a.id,
                "action": a.action,
                "previous_status": a.previous_status,
                "new_status": a.new_status,
                "user_name": a.user_name,
                "organization": a.organization,
                "assigned_team": a.assigned_team,
                "notes": a.notes,
                "timestamp": a.created_at.isoformat(),
            }
            for a in actions
        ],
    }
