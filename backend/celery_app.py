from __future__ import annotations

import os

from celery import Celery
from kombu import Queue


celery_app = Celery("pharmanexus_drug_discovery")

broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("CELERY_BROKER") or "redis://localhost:6379/0"
result_backend = os.getenv("CELERY_RESULT_BACKEND") or os.getenv("CELERY_BROKER_URL") or os.getenv("CELERY_BROKER") or "redis://localhost:6379/1"

celery_app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_queues=(
        Queue("predictions", routing_key="predict"),
        Queue("data_processing", routing_key="data"),
    ),
    task_routes={
        "backend.tasks.prediction_tasks.*": {"queue": "predictions"},
        "backend.data.pubchem_sync.*": {"queue": "data_processing"},
    },
)
