from sqlmodel import SQLModel, create_engine, Session

# SQLite for local dev — zero setup needed!
# Phase 4: swap this for PostgreSQL + pgvector
DATABASE_URL = "sqlite:///khaubot.db"

engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
