from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class TimeRange(BaseModel):
    start: str  # формат "HH:MM"
    end: str    # формат "HH:MM"


class WeeklySchedule(BaseModel):
    mon: List[TimeRange] = Field(default_factory=list)
    tue: List[TimeRange] = Field(default_factory=list)
    wed: List[TimeRange] = Field(default_factory=list)
    thu: List[TimeRange] = Field(default_factory=list)
    fri: List[TimeRange] = Field(default_factory=list)
    sat: List[TimeRange] = Field(default_factory=list)
    sun: List[TimeRange] = Field(default_factory=list)


class Project(BaseModel):
    id: str
    name: str
    business_type: Literal["real_estate", "auto", "services", "goods", "other"]
    timezone: str = "Europe/Moscow"
    enabled: bool = True
    schedule_mode: Literal["always", "by_schedule"] = "always"
    schedule: WeeklySchedule = Field(default_factory=WeeklySchedule)

    tone: Literal["friendly", "neutral", "formal"] = "friendly"
    allow_price_discussion: bool = True
    extra_instructions: Optional[str] = None
