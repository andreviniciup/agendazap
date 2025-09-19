"""
Configuração do banco de dados PostgreSQL
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import logging

from app.config import settings, get_database_url

logger = logging.getLogger(__name__)

# Configurar engine do SQLAlchemy
engine = create_engine(
    get_database_url(),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=300,  # 5 minutos
    echo=settings.DEBUG,  # Log SQL queries em desenvolvimento
)

# Configurar sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# Metadata para migrações
metadata = MetaData()


def get_db():
    """Dependency para obter sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """Inicializar banco de dados"""
    try:
        # Testar conexão
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        
        logger.info("✅ Conexão com PostgreSQL estabelecida")
        
        # Criar tabelas se não existirem
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tabelas do banco de dados verificadas/criadas")
        
    except Exception as e:
        logger.warning(f"⚠️ PostgreSQL não disponível: {e}")
        logger.info("💡 Para desenvolvimento, o servidor continuará sem banco de dados")
        logger.info("💡 Para usar o banco: docker-compose up -d postgres")


def check_db_connection():
    """Verificar se a conexão com o banco está funcionando"""
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"❌ Erro na conexão com o banco: {e}")
        return False


# Configurações específicas para testes
def get_test_db():
    """Database para testes"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    test_engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    return TestingSessionLocal()
