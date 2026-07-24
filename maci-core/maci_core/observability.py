from fastapi import FastAPI
import os
import logging

logger = logging.getLogger(__name__)

def setup_observability(app: FastAPI, service_name: str):
    """
    Injects Prometheus metrics and OpenTelemetry Distributed Tracing into a FastAPI app.
    Fails silently with warning if observability infrastructure is disabled.
    """
    # 1. Prometheus Metrics Configuration
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app)
        logger.info(f"Prometheus metrics exposed for {service_name}")
    except Exception as e:
        logger.warning(f"Prometheus metrics skipped for {service_name}: {e}")
    
    # 2. OpenTelemetry Distributed Tracing
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        jaeger_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger-collector.observability.svc.cluster.local:4317")
        
        resource = Resource(attributes={"service.name": service_name})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=jaeger_endpoint, insecure=True))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        
        FastAPIInstrumentor.instrument_app(app)
        logger.info(f"OpenTelemetry tracing configured for {service_name}")
    except Exception as e:
        logger.warning(f"OpenTelemetry tracing skipped for {service_name}: {e}")
