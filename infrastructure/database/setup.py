from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from tgbot.config import DbConfig


def create_engine(db: DbConfig, db_name: str, echo=False):
    engine = create_async_engine(
        db.construct_sqlalchemy_url(db_name),
        query_cache_size=1200,
        pool_size=20,
        max_overflow=200,
        future=True,
        echo=echo,
        connect_args={
            "autocommit": False,
            "charset": "utf8mb4",
            "use_unicode": True,
            "sql_mode": "TRADITIONAL",
            "connect_timeout": 30,
        },
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
        pool_reset_on_return="commit",
    )
    return engine


def create_session_pool(engine):
    session_pool = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    return session_pool
