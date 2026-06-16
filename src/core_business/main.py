import os
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

SERVICE_NAME = os.getenv("SERVICE_NAME", "core-business")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")

app = FastAPI(
    title="FIT4110 Lab 05 – Core Business Service",
    version=SERVICE_VERSION,
    description=(
        "Policy Engine cho Smart Campus. "
        "Nhận sự kiện từ IoT, Access Gate và AI Vision; áp dụng quy tắc nghiệp vụ; tạo và lưu cảnh báo."
    ),
)


# ── Enums ──────────────────────────────────────────────────────────────────

class AlertSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertType(str, Enum):
    high_temperature = "high_temperature"
    after_hours_access = "after_hours_access"
    unknown_person = "unknown_person"
    high_risk_detection = "high_risk_detection"


# ── Pydantic schemas ────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: str
    instance: Optional[str] = None


class IoTEvent(BaseModel):
    device_id: str = Field(..., min_length=3, examples=["ESP32-LAB-A01"])
    metric: str = Field(..., examples=["temperature"])
    value: float = Field(..., examples=[36.5])
    unit: Optional[str] = Field(default=None, examples=["celsius"])
    timestamp: str = Field(..., examples=["2026-05-13T08:30:00+07:00"])


class AccessEvent(BaseModel):
    card_id: str = Field(..., min_length=3, examples=["RFID-0042"])
    gate_id: str = Field(..., examples=["GATE-A1"])
    direction: str = Field(..., pattern="^(IN|OUT)$", examples=["IN"])
    timestamp: str = Field(..., examples=["2026-05-13T23:15:00+07:00"])


class VisionEvent(BaseModel):
    camera_id: str = Field(..., examples=["CAM-01"])
    objects: List[str] = Field(..., examples=[["person"]])
    confidence: List[float] = Field(..., examples=[[0.95]])
    risk_level: str = Field(..., pattern="^(low|medium|high|critical)$", examples=["high"])
    timestamp: str = Field(..., examples=["2026-05-13T08:30:00+07:00"])


class RuleCreate(BaseModel):
    name: str = Field(..., examples=["High Temperature Rule"])
    condition: str = Field(..., examples=["iot.temperature > threshold"])
    threshold: Optional[float] = Field(default=None, examples=[35.0])


# ── In-memory stores ────────────────────────────────────────────────────────

ALERTS: List[Dict] = []

RULES: List[Dict] = [
    {
        "rule_id": "RULE-001",
        "name": "High Temperature Alert",
        "condition": "iot.temperature > threshold",
        "threshold": 35.0,
        "active": True,
        "created_at": "2026-01-01T00:00:00+00:00",
    },
    {
        "rule_id": "RULE-002",
        "name": "After-hours Access Alert",
        "condition": "access.hour not in [6..21]",
        "threshold": None,
        "active": True,
        "created_at": "2026-01-01T00:00:00+00:00",
    },
    {
        "rule_id": "RULE-003",
        "name": "High Risk Vision Alert",
        "condition": "vision.risk_level in [high, critical]",
        "threshold": None,
        "active": True,
        "created_at": "2026-01-01T00:00:00+00:00",
    },
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
) -> Dict:
    p = {"type": problem_type, "title": title, "status": status_code, "detail": detail}
    if instance:
        p["instance"] = instance
    return p


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_alert_id() -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"ALT-{today}-{len(ALERTS) + 1:04d}"


def _create_alert(
    alert_type: AlertType,
    severity: AlertSeverity,
    message: str,
    source_event: Dict,
) -> Dict:
    alert = {
        "alert_id": next_alert_id(),
        "alert_type": alert_type.value,
        "severity": severity.value,
        "message": message,
        "source_event": source_event,
        "created_at": now_iso(),
    }
    ALERTS.append(alert)
    return alert


# ── Exception handlers ───────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title=status.HTTP_STATUS_CODES.get(exc.status_code, "HTTP Error"),
            detail=str(exc.detail),
            instance=str(request.url.path),
        )
    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", status.HTTP_STATUS_CODES.get(exc.status_code, "HTTP Error"))
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))
    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(i) for i in first_error.get("loc", []))
    message = first_error.get("msg", "Validation error")
    detail = f"{location}: {message}" if location else message
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=detail,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/problems/validation-error",
        ),
        media_type="application/problem+json",
    )


# ── Auth dependency ──────────────────────────────────────────────────────────

def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing Authorization header",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid bearer token",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME, version=SERVICE_VERSION)


@app.post(
    "/events/iot",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_bearer_token)],
    responses={401: {"model": ProblemDetails}, 422: {"model": ProblemDetails}},
)
def process_iot_event(payload: IoTEvent) -> Dict:
    """Nhận dữ liệu từ IoT Ingestion Service; kiểm tra ngưỡng nhiệt độ."""
    generated: List[Dict] = []
    for rule in RULES:
        if not rule["active"]:
            continue
        if (
            rule["condition"] == "iot.temperature > threshold"
            and payload.metric == "temperature"
            and rule["threshold"] is not None
            and payload.value > rule["threshold"]
        ):
            alert = _create_alert(
                AlertType.high_temperature,
                AlertSeverity.high,
                f"Temperature {payload.value} vượt ngưỡng {rule['threshold']} trên thiết bị {payload.device_id}",
                payload.model_dump(),
            )
            generated.append(alert)
    return {
        "processed": True,
        "event_type": "iot",
        "alerts_generated": len(generated),
        "alerts": generated,
    }


@app.post(
    "/events/access",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_bearer_token)],
    responses={401: {"model": ProblemDetails}, 422: {"model": ProblemDetails}},
)
def process_access_event(payload: AccessEvent) -> Dict:
    """Nhận sự kiện quẹt thẻ từ Access Gate; kiểm tra truy cập ngoài giờ (22:00–05:59)."""
    generated: List[Dict] = []
    try:
        dt = datetime.fromisoformat(payload.timestamp)
        hour = dt.hour
        if hour >= 22 or hour < 6:
            alert = _create_alert(
                AlertType.after_hours_access,
                AlertSeverity.medium,
                f"Thẻ {payload.card_id} quẹt tại cổng {payload.gate_id} ngoài giờ cho phép (giờ={hour}:00)",
                payload.model_dump(),
            )
            generated.append(alert)
    except ValueError:
        pass
    return {
        "processed": True,
        "event_type": "access",
        "alerts_generated": len(generated),
        "alerts": generated,
    }


@app.post(
    "/events/vision",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_bearer_token)],
    responses={401: {"model": ProblemDetails}, 422: {"model": ProblemDetails}},
)
def process_vision_event(payload: VisionEvent) -> Dict:
    """Nhận kết quả phân tích hình ảnh từ AI Vision; tạo cảnh báo khi rủi ro cao."""
    generated: List[Dict] = []
    if payload.risk_level in ("high", "critical"):
        severity = AlertSeverity.critical if payload.risk_level == "critical" else AlertSeverity.high
        alert = _create_alert(
            AlertType.high_risk_detection,
            severity,
            f"Camera {payload.camera_id} phát hiện {', '.join(payload.objects)} với rủi ro {payload.risk_level}",
            payload.model_dump(),
        )
        generated.append(alert)
    return {
        "processed": True,
        "event_type": "vision",
        "alerts_generated": len(generated),
        "alerts": generated,
    }


@app.get(
    "/alerts",
    dependencies=[Depends(verify_bearer_token)],
    responses={401: {"model": ProblemDetails}},
)
def list_alerts(
    limit: int = Query(default=10, ge=1, le=100),
    severity: Optional[str] = Query(default=None),
    alert_type: Optional[str] = Query(default=None),
) -> Dict:
    """Trả về danh sách cảnh báo đã tạo; có thể lọc theo severity hoặc alert_type."""
    items = ALERTS
    if severity:
        items = [a for a in items if a["severity"] == severity]
    if alert_type:
        items = [a for a in items if a["alert_type"] == alert_type]
    return {"items": items[-limit:], "total": len(ALERTS)}


@app.get(
    "/rules",
    dependencies=[Depends(verify_bearer_token)],
    responses={401: {"model": ProblemDetails}},
)
def list_rules() -> Dict:
    """Trả về danh sách quy tắc nghiệp vụ đang hoạt động."""
    return {"items": RULES, "total": len(RULES)}


@app.post(
    "/rules",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
    responses={401: {"model": ProblemDetails}, 422: {"model": ProblemDetails}},
)
def create_rule(payload: RuleCreate) -> Dict:
    """Thêm một quy tắc nghiệp vụ mới."""
    rule = {
        "rule_id": f"RULE-{len(RULES) + 1:03d}",
        "name": payload.name,
        "condition": payload.condition,
        "threshold": payload.threshold,
        "active": True,
        "created_at": now_iso(),
    }
    RULES.append(rule)
    return rule
