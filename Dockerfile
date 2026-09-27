FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/staticfiles /app/media && chown -R app:app /app
USER app
RUN DEBUG=0 SECRET_KEY=build-only-not-used-at-runtime python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn","config.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","60","--access-logfile","-"]
