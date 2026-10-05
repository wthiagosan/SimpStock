# ==============================================================================
# SimpStock - Dockerfile Otimizado para Produção (Google Cloud Run)
# ==============================================================================
FROM python:3.12-slim

# Variáveis de ambiente para execução otimizada e sem buffer do Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Diretório de trabalho da aplicação
WORKDIR /app

# Utilitários mínimos do sistema operacional e limpeza imediata de cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criação de usuário não-privilegiado para conformidade com segurança do Cloud Run
RUN groupadd -r simpstock && useradd -r -g simpstock -d /app -s /sbin/nologin simpstock

# Instalação das dependências Python em camada isolada
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Cópia integral do código-fonte
COPY . .

# Ajuste de propriedade para o usuário de execução
RUN chown -R simpstock:simpstock /app

# Comuta para usuário não-root
USER simpstock

# Porta documentada para o Cloud Run
EXPOSE 8080

# Healthcheck de conformidade para orquestradores de contêiner
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/ || exit 1

# Inicialização do Gunicorn com binding dinâmico na variável $PORT do Cloud Run (fallback 8080)
CMD exec gunicorn \
    --bind 0.0.0.0:${PORT:-8080} \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app