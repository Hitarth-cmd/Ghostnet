from __future__ import annotations

import enum


class ObjectClass(str, enum.Enum):
    MARINE_DEBRIS = "marine_debris"
    SUSPECTED_GHOST_GEAR = "suspected_ghost_gear"
    UNKNOWN_FLOATING_OBJECT = "unknown_floating_object"


class DetectionStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    ASSIGNED = "assigned"
    BEING_HANDLED = "being_handled"
    RESOLVED = "resolved"
    RECOVERED = "recovered"
    REJECTED = "rejected"


class UserRole(str, enum.Enum):
    NGO = "ngo"
    RESPONDER = "responder"
    RESEARCHER = "researcher"
    COAST_GUARD = "coast_guard"
    ADMIN = "admin"


class AlertSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AlertStatus(str, enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PriorityLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ForcingMode(str, enum.Enum):
    DEMO = "demo"
    LIVE = "live"


class SpatialFeatureType(str, enum.Enum):
    PROTECTED_AREA = "protected_area"
    HABITAT = "habitat"
    COASTLINE = "coastline"
    CORAL_REEF = "coral_reef"
    SPECIES_SANCTUARY = "species_sanctuary"

