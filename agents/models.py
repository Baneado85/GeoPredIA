from datetime import datetime, timezone, timedelta
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Weights(Model):
    geological: float = Field(default=.40, ge=0, le=1)
    environmental: float = Field(default=.35, ge=0, le=1)
    social: float = Field(default=.25, ge=0, le=1)

    @model_validator(mode="after")
    def normalized(self):
        if abs(sum((self.geological, self.environmental, self.social)) - 1) > .000001:
            raise ValueError("Los pesos deben sumar 1 (100 %).")
        return self


class EvaluationRequest(Model):
    zone_id: str = Field(min_length=1, max_length=64)
    weights: Weights = Field(default_factory=Weights)


class AgentRequest(Model):
    evaluation_id: str = Field(min_length=1, max_length=64)


class AssistantQuery(Model):
    zone_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def useful_question(cls, value):
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Escribe una pregunta concreta.")
        return value


class ReviewRequest(AgentRequest):
    reviewer: str = Field(min_length=2, max_length=100)
    decision: Literal["approved", "observed", "rejected"]
    justification: str = Field(min_length=12, max_length=3000)

    @field_validator("reviewer", "justification")
    @classmethod
    def non_blank(cls, value, info):
        value = value.strip()
        if len(value) < (2 if info.field_name == "reviewer" else 12):
            raise ValueError("Escribe un nombre y una justificación concreta.")
        return value


class WorkflowCallback(ReviewRequest):
    workflow_instance_id: str = Field(min_length=1, max_length=128)


class Readings(Model):
    air_temperature_c: float | None = Field(default=None, ge=-40, le=85)
    air_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    soil_moisture_pct: float | None = Field(default=None, ge=0, le=100)
    water_temperature_c: float | None = Field(default=None, ge=-55, le=125)


class TelemetryRequest(Model):
    device_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    zone_id: str = Field(min_length=1, max_length=64)
    observed_at: datetime
    source: Literal["device", "simulator"]
    readings: Readings

    @field_validator("observed_at")
    @classmethod
    def aware_timestamp(cls, value):
        if value.tzinfo is None:
            raise ValueError("observed_at debe incluir la zona horaria UTC.")
        if value > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("La lectura está fechada en el futuro.")
        return value


class SimulationRequest(Model):
    zone_id: str = Field(min_length=1, max_length=64)


class CSVImport(Model):
    csv: str = Field(min_length=1, max_length=500_000)
