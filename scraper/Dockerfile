FROM python:3.9-slim

WORKDIR /app

# Copiar arquivos de requisitos e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código-fonte
COPY src/ ./src/

# Criar diretório para dados
RUN mkdir -p ./data

# Comando para executar o scraper
ENTRYPOINT ["python", "-m", "src.main"]
CMD [] 