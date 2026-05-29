FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    gdal-bin \
    libspatialindex-dev \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY WebApp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY WebApp/ .

RUN mkdir -p cache

EXPOSE 10000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
