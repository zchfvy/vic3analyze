import os
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

db_file = 'vic3.db'
_engine = []

class Base(DeclarativeBase):
    pass


def get_db():
    if not _engine:
        db_full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', db_file))
        must_instantiate = not os.path.exists(db_full_path)
        engine = create_engine(f"sqlite:///{db_full_path}")

        if must_instantiate:
            Base.metadata.create_all(engine)

        _engine.append(engine)
    return _engine[0]


if __name__ == '__main__':
    get_db()
