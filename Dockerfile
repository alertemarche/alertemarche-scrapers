FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dépendances système minimales pour lxml.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libxml2-dev libxslt1-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Utilisateur non-root.
RUN useradd -m scraper && chown -R scraper:scraper /app
USER scraper

# Par défaut : planificateur en continu. Override possible : `python run_all.py`.
CMD ["python", "scheduler.py"]
