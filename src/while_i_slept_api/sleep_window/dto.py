"""DTOs for sleep-window calculation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SleepWindow(BaseModel):
    """Most recent completed sleep window."""

    start: datetime
    end: datetime
