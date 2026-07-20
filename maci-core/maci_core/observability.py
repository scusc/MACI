from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import os

def setup_observability(app: FastAPI, service_name: str):
    """
    Injects Prometheus metrics and OpenTelemetry Distributed Tracing into a FastAPI app.
    """
    # 1. Prometheus Metrics Configuration
    # Automatically exposes /metrics endpoint to scrape request counts, latency, and system IO
    Instrumentator().instrument(app).expose(app)
    
    # 2. OpenTelemetry Distributed Tracing
    # The Jaeger endpoint is typically injected via ENV vars in Kubernetes. 
    # Defaulting to localhost for local testing.
    jaeger_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger-collector.observability.svc.cluster.local:4317")
    
    resource = Resource(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=jaeger_endpoint, insecure=True))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    # Instrument the FastAPI app so every request generates a span
    FastAPIInstrumentor.instrument_app(app)
