# Dockerfile
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Répertoire de travail
WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirements/ /app/requirements/

# Installer les dépendances Python
RUN pip install --upgrade pip && \
    pip install -r requirements/production.txt

# Copier le projet
COPY . /app/

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput

# Créer un utilisateur non-root
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Exposer le port
EXPOSE 8000

# Commande de démarrage
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]