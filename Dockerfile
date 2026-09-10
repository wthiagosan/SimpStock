# ============================================================
#  SimpStock - Production Dockerfile (Python 3.12 Slim)
# ============================================================
FROM python:3.12-slim AS base

# Previne criação de arquivos .pyc e força stdout imediato
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    FLASK_ENV=production

WORKDIR /app

# Instala dependências do sistema necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root para execução segura do container
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app appuser

# Copia dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Assegura permissões adequadas
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 5000

# Healthcheck no endpoint raiz da API
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "app:create_app()"]