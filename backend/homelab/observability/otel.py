"""OpenTelemetry initialization helpers."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from homelab.config import get_settings


settings = get_settings()


def configure_otel(app, engine) -> None:
    """Configure OpenTelemetry tracing for the app and clients."""
    resource = Resource.create({"service.name": settings.otel_service_name})
    tracer_provider = TracerProvider(resource=resource)

    if settings.otel_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint, insecure=True)
    else:
        exporter = OTLPSpanExporter()
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
