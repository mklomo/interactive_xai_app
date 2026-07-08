from typing import Optional, List
from datetime import datetime
from backend.timing import StageTiming


class TimingService:
    def __init__(self, database):
        self.database = database

    def record_start_time(self, user_id: int, stage: str) -> None:
        """Record start time only the first time."""
        query = """
            INSERT INTO user_stage_timings (user_id, stage, start_time, updated_at)
            VALUES (:user_id, :stage, :start_time, NOW())
            ON CONFLICT (user_id, stage) 
            DO UPDATE SET 
                start_time = COALESCE(user_stage_timings.start_time, EXCLUDED.start_time),
                updated_at = NOW()
            RETURNING id
        """
        params = {
            'user_id': user_id,
            'stage': stage,
            'start_time': datetime.now()
        }
        self.database.execute_query(query, params, write=True)   # Now safe

    def record_end_time(self, user_id: int, stage: str) -> None:
        """Record/update end time."""
        query = """
            INSERT INTO user_stage_timings (user_id, stage, end_time, updated_at)
            VALUES (:user_id, :stage, :end_time, NOW())
            ON CONFLICT (user_id, stage) 
            DO UPDATE SET 
                end_time = EXCLUDED.end_time,
                updated_at = NOW()
            RETURNING id
        """
        params = {
            'user_id': user_id,
            'stage': stage,
            'end_time': datetime.now()
        }
        self.database.execute_query(query, params, write=True)   # Now safe

    def get_stage_timing(self, user_id: int, stage: str) -> Optional[StageTiming]:
        query = """
            SELECT id, user_id, stage, start_time, end_time, created_at, updated_at
            FROM user_stage_timings
            WHERE user_id = :user_id AND stage = :stage
        """
        params = {'user_id': user_id, 'stage': stage}
        results = self.database.execute_query(query, params)

        if not results or len(results) == 0:
            return None

        row = results[0]
        return StageTiming(
            id=row[0],
            user_id=row[1],
            stage=row[2],
            start_time=row[3],
            end_time=row[4],
            created_at=row[5],
            updated_at=row[6],
        )

    def get_all_timings_for_user(self, user_id: int) -> List[StageTiming]:
        query = """
            SELECT id, user_id, stage, start_time, end_time, created_at, updated_at
            FROM user_stage_timings
            WHERE user_id = :user_id
            ORDER BY stage
        """
        params = {'user_id': user_id}
        results = self.database.execute_query(query, params)

        return [
            StageTiming(
                id=row[0], user_id=row[1], stage=row[2],
                start_time=row[3], end_time=row[4],
                created_at=row[5], updated_at=row[6]
            )
            for row in results
        ]

    def get_stage_duration(self, user_id: int, stage: str) -> Optional[str]:
        timing = self.get_stage_timing(user_id, stage)
        if timing and timing.start_time and timing.end_time:
            return str(timing.end_time - timing.start_time)
        return None