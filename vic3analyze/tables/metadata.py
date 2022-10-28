from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

class RunMetadata(Base):
    __tablename__ = 'runs'

    # id is a surrogate key
    id: Mapped[str] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column()

    start_time_wall: Mapped[datetime] = mapped_column(DateTime)

    @staticmethod
    def collect(replay_data):
        ml = replay_data['mainlist']
        meta = ml['meta_data']
        return RunMetadata(
                id=ml['playthrough_id'],
                game_version=meta['version'],
                start_time_wall=None)


class SampleMetadata(Base):
    __tablename__ = 'samples'

    game_date: Mapped[datetime] = mapped_column(DateTime(timezone=False), primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), primary_key=True)
    run: Mapped["RunMetadata"] = relationship()

    wall_time: Mapped[datetime] = mapped_column(DateTime)
    sample_cap_time_seconds: Mapped[int] = mapped_column()

    @staticmethod
    def collect(replay_data, run_obj):
        # TODO : assertation that run_obj actually comes from the same replay
        ml = replay_data['mainlist']
        meta = ml['meta_data']
        return SampleMetadata(
                run=run_obj,
                run_id=ml['playthrough_id'],
                game_date=ml['date'],
                sample_cap_time_seconds=None,
                wall_time=None)
