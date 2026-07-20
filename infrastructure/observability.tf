# ── Kubernetes Observability Stack ────────────────────────────────────
#
# 🎓 LESSON: SRE Observability
# In an enterprise cluster, you need to monitor CPU, memory, and application metrics.
# We deploy the industry standard `kube-prometheus-stack` via Helm.
# This includes:
#   1. Prometheus (Time-series database for metrics)
#   2. Grafana (Dashboard visualization)
#   3. AlertManager (Alerting logic)

resource "kubernetes_namespace" "observability" {
  metadata {
    name = "observability"
  }
}

resource "helm_release" "prometheus" {
  name       = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = kubernetes_namespace.observability.metadata[0].name
  version    = "58.2.2"

  # Wait for the AKS cluster to be fully provisioned before installing Helm charts
  depends_on = [azurerm_kubernetes_cluster.aks]

  # Disable components we don't need to save memory on our small cluster
  set {
    name  = "alertmanager.enabled"
    value = "false"
  }

  set {
    name  = "grafana.enabled"
    value = "true"
  }
  
  # Allow Prometheus to scrape ServiceMonitors from any namespace
  set {
    name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
    value = "false"
  }
}

# ── Jaeger (Distributed Tracing) ──────────────────────────────────────
# 🎓 LESSON: Distributed Tracing
# Tracing tracks a single user request as it traverses multiple microservices.
# Jaeger provides the UI to view these spans. OpenTelemetry in FastAPI sends spans here.

resource "helm_release" "jaeger" {
  name       = "jaeger"
  repository = "https://jaegertracing.github.io/helm-charts"
  chart      = "jaeger"
  namespace  = kubernetes_namespace.observability.metadata[0].name
  version    = "3.0.3"

  depends_on = [azurerm_kubernetes_cluster.aks]

  set {
    name  = "provisionDataStore.cassandra"
    value = "false"
  }

  set {
    name  = "allInOne.enabled"
    value = "true"
  }

  set {
    name  = "storage.type"
    value = "memory" # In-memory for dev/testing. Production would use Elasticsearch.
  }
}
