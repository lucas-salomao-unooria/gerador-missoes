# Dockerfile otimizado para o Gerador de Missões Unooria (Streamlit + Google ADK + Cloud Run)
FROM python:3.11-slim

# Hora de Brasília em tudo que o app mostra ou grava (expiração do login, data dos pareceres, criação
# da missão, nome da pasta): o Cloud Run roda em UTC, e o horário saía 3 h adiantado. O `tzdata`
# abaixo é garantia: a imagem base de hoje já traz a base de fusos, mas sem ela o TZ cai em UTC calado.
ENV TZ=America/Sao_Paulo \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8080 \
    STREAMLIT_SERVER_PORT=8080 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_FILE_WATCHER_TYPE=none \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Instala curl, git e Node.js para o proxy do MCP do Stitch (npx)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    tzdata \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Garante a existência do diretório de saída
RUN mkdir -p /app/output

EXPOSE 8080

# Pré-importa `app` durante o startup (aproveitando `--startup-cpu-boost` antes do probe TCP na 8080
# liberar tráfego e instalando o fallback de `/media/<id>.html` já no boot) e desativa o file watcher
# (`--server.fileWatcherType=none`) para que o `InotifyObserver` não faça `os.walk("/app")` sobre os
# buckets GCSFuse montados em `/app/output` e `/app/base-plataforma`.
CMD ["python", "-c", "import sys, app; from streamlit.web.cli import main; sys.argv = ['streamlit', 'run', 'app.py', '--server.port=8080', '--server.address=0.0.0.0', '--server.fileWatcherType=none']; sys.exit(main())"]
