from datetime import datetime
import json
import os
import sys
import logging
import time

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

import tables
from parse import parse
from database import get_db

log = logging.getLogger(__name__)

class DuplicateSampleError(Exception):
    pass

def process(save_file):
    time_cap_start = time.time()

    # Setup collectors here, before we load the DB
    from tables.country_basics import CountryBasics
    from tables.market_goods import MarketGoods
    collectors = [CountryBasics, MarketGoods]

    log.info(f"Parsing save file: {save_file}")
    parsed = parse(save_file)

    # Run collection before connecting to DB

    log.info(f"Collecting replay metadata")
    from tables.metadata import RunMetadata, SampleMetadata
    run_meta = RunMetadata.collect(parsed)

    with Session(get_db()) as session:
        stmt = select(RunMetadata).where(RunMetadata.id == run_meta.id)
        existing_run = session.scalars(stmt).first()
        if existing_run is not None:
            run_meta = existing_run

    sample_meta = SampleMetadata.collect(parsed, run_meta)

    with Session(get_db()) as session:
        stmt = select(SampleMetadata).where(
                and_(
                SampleMetadata.game_date == sample_meta.game_date,
                SampleMetadata.run_id == sample_meta.run_id,
                ))
        existing_sample = session.scalars(stmt).first()
        if existing_sample is not None:
            log.error("Found a sample matching the current one already in the db!")
            raise DuplicateSampleError()


    log.info(f"Collecting replay primary data")
    collected_data = []
    for col_cls in collectors:
        data = col_cls.collect(parsed, sample_meta, run_meta)
        collected_data.extend(data)

    time_cap_end = time.time()
    cap_duration = time_cap_end - time_cap_start
    log.info(f"Collected {len(collected_data)} data points in {cap_duration} seconds")

    # set some final vars
    run_meta.start_time_wall = datetime.now()
    sample_meta.wall_time = datetime.now()
    sample_meta.sample_cap_time_seconds = cap_duration

    log.info(f"Writing to database")
    with Session(get_db()) as session:
        if existing_run is None:
            session.add_all([run_meta])
        session.add_all([sample_meta])
        session.add_all(collected_data)
        session.commit()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    fname = sys.argv[1]
    process(os.path.expanduser(fname))
