FROM python:3.12-slim

# System deps required by geopandas/shapely/rasterio (GDAL/GEOS/PROJ).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev libgeos-dev libproj-dev gcc g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app /app/app
COPY configs /app/configs
COPY data /app/data

ENV PYTHONPATH=/app
ENV GHOSTNET_DATA_ROOT=/app/data/demo
ENV GHOSTNET_KNOWLEDGE_BASE=/app/data/knowledge_base
ENV GHOSTNET_RISK_CONFIG=/app/configs/risk.yaml

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
