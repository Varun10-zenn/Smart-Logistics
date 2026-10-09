"""Safety service."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.safety import SafetyEvent, SafetyScore, SafetyAlert
from backend.app.models.telemetry import TelemetryEvent
from backend.app.models.delivery import Delivery
from backend.app.schemas.common import make_page
from backend.app.schemas.safety import SafetyScoreRead, SafetyEventRead, SafetyAlertRead

SAFETY_SPEED_THRESHOLD = 80.0
HARSH_BRAKING_THRESHOLD = -4.0
HARSH_ACCELERATION_THRESHOLD = 4.0
ROUTE_DEVIATION_THRESHOLD = 1.0


def analyze_telemetry(db: Session, event: TelemetryEvent):
    delivery = db.query(Delivery).filter(Delivery.id == event.delivery_id).first()
    if not delivery:
        return

    events_created = []

    if float(event.speed_kmh) > SAFETY_SPEED_THRESHOLD:
        sev = SafetyEvent(
            delivery_id=delivery.id,
            event_type="speeding",
            severity="high" if float(event.speed_kmh) > 100 else "medium",
            timestamp=event.timestamp,
            latitude=event.latitude,
            longitude=event.longitude,
            observed_value=float(event.speed_kmh),
            threshold_value=SAFETY_SPEED_THRESHOLD,
            penalty_points=2.0
        )
        db.add(sev)
        events_created.append(sev)

    if float(event.acceleration_mpss) < HARSH_BRAKING_THRESHOLD:
        sev = SafetyEvent(
            delivery_id=delivery.id,
            event_type="harsh_braking",
            severity="high",
            timestamp=event.timestamp,
            latitude=event.latitude,
            longitude=event.longitude,
            observed_value=float(event.acceleration_mpss),
            threshold_value=HARSH_BRAKING_THRESHOLD,
            penalty_points=3.0
        )
        db.add(sev)
        events_created.append(sev)

    if float(event.acceleration_mpss) > HARSH_ACCELERATION_THRESHOLD:
        sev = SafetyEvent(
            delivery_id=delivery.id,
            event_type="harsh_acceleration",
            severity="medium",
            timestamp=event.timestamp,
            latitude=event.latitude,
            longitude=event.longitude,
            observed_value=float(event.acceleration_mpss),
            threshold_value=HARSH_ACCELERATION_THRESHOLD,
            penalty_points=1.5
        )
        db.add(sev)
        events_created.append(sev)

    if not events_created:
        return

    score = db.query(SafetyScore).filter(SafetyScore.delivery_id == delivery.id).first()
    if not score:
        score = SafetyScore(
            delivery_id=delivery.id,
            final_score=100.0,
            speed_compliance_score=100.0,
            braking_score=100.0,
            acceleration_score=100.0,
            route_adherence_score=100.0
        )
        db.add(score)

    for sev in events_created:
        if sev.event_type == "speeding":
            score.speed_compliance_score = float(score.speed_compliance_score) - float(sev.penalty_points)
        elif sev.event_type == "harsh_braking":
            score.braking_score = float(score.braking_score) - float(sev.penalty_points)
        elif sev.event_type == "harsh_acceleration":
            score.acceleration_score = float(score.acceleration_score) - float(sev.penalty_points)

    score.speed_compliance_score = max(0.0, float(score.speed_compliance_score))
    score.braking_score = max(0.0, float(score.braking_score))
    score.acceleration_score = max(0.0, float(score.acceleration_score))
    score.final_score = (score.speed_compliance_score + score.braking_score + score.acceleration_score + float(score.route_adherence_score)) / 4.0
    
    # ── Safety Alerts with 5-Minute Deduplication ──
    from datetime import datetime, timedelta, timezone
    from backend.app.core.config import settings

    def _create_alert_if_not_deduped(alert_type: str, severity: str, message: str):
        five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
        existing = db.query(SafetyAlert).filter(
            SafetyAlert.delivery_id == delivery.id,
            SafetyAlert.alert_type == alert_type,
            SafetyAlert.created_at >= five_mins_ago
        ).first()
        if not existing:
            alert = SafetyAlert(
                delivery_id=delivery.id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                created_at=datetime.utcnow()
            )
            db.add(alert)

    # Check high-severity safety events
    for sev in events_created:
        if sev.severity == "high":
            msg = f"{sev.event_type.replace('_', ' ').capitalize()} observed: {float(sev.observed_value):.1f} (threshold: {float(sev.threshold_value):.1f})"
            _create_alert_if_not_deduped(sev.event_type, "high", msg)

    # Check overall safety score threshold
    alert_score_threshold = getattr(settings, "SAFETY_ALERT_SCORE", 70.0)
    if score.final_score < alert_score_threshold:
        msg = f"Delivery safety score dropped to {score.final_score:.1f} (below threshold {alert_score_threshold:.1f})"
        _create_alert_if_not_deduped("low_score", "critical", msg)

    db.commit()

def _score_read(s: SafetyScore) -> SafetyScoreRead:
    return SafetyScoreRead(
        id=s.id,
        delivery_id=s.delivery_id,
        score=float(s.final_score),
        speed_score=float(s.speed_compliance_score),
        braking_score=float(s.braking_score),
        acceleration_score=float(s.acceleration_score),
        route_score=float(s.route_adherence_score),
        calculated_at=s.calculated_at,
    )


def _event_read(e: SafetyEvent) -> SafetyEventRead:
    return SafetyEventRead(
        id=e.id,
        delivery_id=e.delivery_id,
        event_type=e.event_type,
        severity=e.severity,
        timestamp=e.timestamp,
        latitude=float(e.latitude),
        longitude=float(e.longitude),
        value=float(e.observed_value),
        threshold=float(e.threshold_value),
    )


def _alert_read(a: SafetyAlert) -> SafetyAlertRead:
    return SafetyAlertRead(
        id=a.id,
        delivery_id=a.delivery_id,
        alert_type=a.alert_type,
        severity=a.severity,
        message=a.message,
        acknowledged=a.is_acknowledged,
        created_at=a.created_at,
    )


def list_scores(db: Session, page: int = 1, page_size: int = 20,
                delivery_id: int = None, driver_id: int = None):
    q = db.query(SafetyScore)
    if delivery_id:
        q = q.filter(SafetyScore.delivery_id == delivery_id)
    total = q.count()
    scores = q.order_by(SafetyScore.calculated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_score_read(s) for s in scores], total, page, page_size)


def get_score_by_delivery(db: Session, delivery_id: int) -> SafetyScoreRead:
    score = db.query(SafetyScore).filter(SafetyScore.delivery_id == delivery_id).first()
    if score is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Safety score not found for this delivery.", "details": {}})
    return _score_read(score)


def list_events(db: Session, page: int = 1, page_size: int = 20,
                delivery_id: int = None):
    q = db.query(SafetyEvent)
    if delivery_id:
        q = q.filter(SafetyEvent.delivery_id == delivery_id)
    total = q.count()
    events = q.order_by(SafetyEvent.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_event_read(e) for e in events], total, page, page_size)


def list_alerts(db: Session, page: int = 1, page_size: int = 20,
                delivery_id: int = None, acknowledged: bool = None):
    q = db.query(SafetyAlert)
    if delivery_id:
        q = q.filter(SafetyAlert.delivery_id == delivery_id)
    if acknowledged is not None:
        q = q.filter(SafetyAlert.is_acknowledged == acknowledged)
    total = q.count()
    alerts = q.order_by(SafetyAlert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_alert_read(a) for a in alerts], total, page, page_size)


def acknowledge_alert(db: Session, alert_id: int) -> SafetyAlertRead:
    alert = db.query(SafetyAlert).filter(SafetyAlert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Safety alert not found.", "details": {}})
    alert.is_acknowledged = True
    db.commit()
    db.refresh(alert)
    return _alert_read(alert)
