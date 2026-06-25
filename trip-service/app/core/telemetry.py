"""
Distributed Tracing / Telemetry Module

Integrates OpenTelemetry to capture the execution graph of our LangChain swarms.
This allows us to see exactly how long each AI step took, how many tokens were used,
and where the bottlenecks are in the negotiation process.
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# In a production environment, you would use Azure Monitor / Application Insights Exporter
# from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
# exporter = AzureMonitorTraceExporter.from_connection_string(os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"))

def init_telemetry():
    """Initializes OpenTelemetry tracing."""
    provider = TracerProvider()
    
    # For local dev / MVP, we just export to console so we can see the traces in Kubernetes logs
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
    print("OpenTelemetry Tracing Initialized")

def get_tracer(name: str):
    """Gets a tracer for a specific module."""
    return trace.get_tracer(name)
