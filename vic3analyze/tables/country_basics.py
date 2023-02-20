from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

class CountryBasics(Base):
    __tablename__ = "country_basics"

    run_id: Mapped[int] = mapped_column(ForeignKey('runs.id'), primary_key=True)
    game_date: Mapped[datetime] = mapped_column(ForeignKey('samples.game_date'), primary_key=True)
    sample: Mapped["SampleMetadata"] = relationship()
    run: Mapped["RunMetadata"] = relationship()

    tag: Mapped[str] = mapped_column(primary_key=True)
    db_id: Mapped[int] = mapped_column(primary_key=True)

    gdp: Mapped[float] = mapped_column()
    prestige: Mapped[float] = mapped_column()
    standard_of_living: Mapped[float] = mapped_column()
    population: Mapped[int] = mapped_column()
    radicals: Mapped[int] = mapped_column()
    loyalists: Mapped[int] = mapped_column()
    treasury: Mapped[float] = mapped_column()
    investment_pool: Mapped[float] = mapped_column()
    credit_limit: Mapped[float] = mapped_column()


    @staticmethod
    def collect(replay_data, sample_obj, run_obj):
        ml = replay_data

        country_db = ml['country_manager']['database']
        for k, v in ml['country_manager']['database'].items():
            if isinstance(v, dict):
                ps = v['pop_statistics']
                bud = v['budget']
                yield CountryBasics(
                    sample = sample_obj,
                    run = run_obj,

                    tag = v['definition'],
                    db_id = int(k),

                    gdp = get_sampledata(v['gdp']),
                    prestige = get_sampledata(v['prestige']),
                    standard_of_living = get_sampledata(v['avgsoltrend']),
                    population = get_sampledata(ps['population_trend']),
                    radicals = get_sampledata(ps['radical_trend']),
                    loyalists = get_sampledata(ps['loyalist_trend']),
                    treasury = bud['money'],
                    investment_pool = bud.get('investment_pool',0),
                    credit_limit = bud['credit']
                )


def get_sampledata(samp_in):
    # TODO : probably should have ab etter solution than zero when not found!
    if 'channels' not in samp_in:
        return 0
    return samp_in['channels']["0"]['values'][-1]
