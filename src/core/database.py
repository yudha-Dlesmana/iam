from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings

engine = create_async_engine(
    # ═══════════════════════════════════
    # CONNECTION
    # ═══════════════════════════════════
    url=settings.DB_URL,         

    # ═══════════════════════════════════
    # POOL — kapasitas
    # ═══════════════════════════════════
    poolclass=AsyncAdaptedQueuePool,     
    pool_size=5,                         
    max_overflow=10,                     

    # ═══════════════════════════════════
    # POOL — antrian & timeout
    # ═══════════════════════════════════
    pool_timeout=30,                     

    # ═══════════════════════════════════
    # POOL — health & lifecycle
    # ═══════════════════════════════════
    pool_recycle=3600,                   
    pool_pre_ping=True,                  
    pool_use_lifo=False,                 
    pool_reset_on_return="rollback",     

    # ═══════════════════════════════════
    # LOGGING
    # ═══════════════════════════════════
    echo=False,                          
    echo_pool=False,                     
    hide_parameters=False,               
    logging_name=None,                   

    # ═══════════════════════════════════
    # PERFORMANCE
    # ═══════════════════════════════════
    query_cache_size=500,                
    isolation_level=None,                
    future=True, 

    # ═══════════════════════════════════
    # CONNECTION ARGS (driver-specific)
    # ═══════════════════════════════════
    connect_args={
        "charset": "utf8mb4",
        # SSL kalau perlu:
        # "ssl": {"ca": "/path/cert.pem"},
    },

    # ═══════════════════════════════════
    # EXECUTION DEFAULTS
    # ═══════════════════════════════════
    execution_options={
        "compiled_cache": {},
        # "isolation_level": "REPEATABLE READ",
        # "schema_translate_map": {"old": "new"},
    },                        
)

SessionLocal = async_sessionmaker(
    # ═══════════════════════════════════
    # BIND
    # ═══════════════════════════════════
    bind=engine, 
    class_=AsyncSession,

    # ═══════════════════════════════════
    # FLUSH BEHAVIOR
    # ═══════════════════════════════════
    autoflush=True,
    expire_on_commit=False,
    autobegin=True,

    # ═══════════════════════════════════
    # TRANSACTION
    # ═══════════════════════════════════
    twophase=False,
    join_transaction_mode="conditional_savepoint",

    # ═══════════════════════════════════
    # ROUTING (multi-engine)
    # ═══════════════════════════════════
    binds=None,

    # ═══════════════════════════════════
    # METADATA
    # ═══════════════════════════════════
    info={"app": "fastapi-starter"},

    # ═══════════════════════════════════
    # ASYNC SPECIFIC
    # ═══════════════════════════════════
    sync_session_class=None,
    close_resets_only=False
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session