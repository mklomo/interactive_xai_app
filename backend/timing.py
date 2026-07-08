from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class StageTiming:
    """
    Model representing timing data for one stage of a user.
    """
    id: Optional[int] = None
    user_id: int = None
    stage: str = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None