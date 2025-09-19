"""
AgendaZap - Main FastAPI Application
Sistema de agendamento de serviços com automação WhatsApp
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.api import auth, users, services, appointments, clients, webhooks

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup
    logger.info("🚀 Iniciando AgendaZap Backend...")
    await init_db()
    logger.info("✅ Banco de dados inicializado")
    
    yield
    
    # Shutdown
    logger.info("🛑 Finalizando AgendaZap Backend...")


# Criar aplicação FastAPI
app = FastAPI(
    title="AgendaZap API",
    description="Sistema de agendamento de serviços com automação WhatsApp",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar Trusted Host
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )


# Middleware de logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para logar todas as requisições"""
    start_time = time.time()
    
    # Log da requisição
    logger.info(f"📥 {request.method} {request.url.path} - {request.client.host}")
    
    # Processar requisição
    response = await call_next(request)
    
    # Log da resposta
    process_time = time.time() - start_time
    logger.info(f"📤 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response


# Middleware de error handling global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global para exceções não tratadas"""
    logger.error(f"❌ Erro não tratado: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erro interno do servidor",
            "message": "Ocorreu um erro inesperado. Tente novamente mais tarde.",
            "timestamp": time.time()
        }
    )


# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Endpoint para verificar saúde da aplicação"""
    return {
        "status": "healthy",
        "service": "AgendaZap Backend",
        "version": "1.0.0",
        "timestamp": time.time()
    }


# Incluir routers da API
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticação"])
app.include_router(users.router, prefix="/api/users", tags=["Usuários"])
app.include_router(services.router, prefix="/api/services", tags=["Serviços"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["Agendamentos"])
app.include_router(clients.router, prefix="/api/clients", tags=["Clientes"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])


# Root endpoint
@app.get("/")
async def root():
    """Endpoint raiz da API"""
    return {
        "message": "AgendaZap API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "Documentação não disponível em produção"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )
