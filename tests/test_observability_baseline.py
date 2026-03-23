from pathlib import Path


def test_observability_baseline_uses_alloy_and_otlp_defaults() -> None:
    prod_compose = Path("/workspace/docker-compose.yml").read_text(encoding="utf-8")
    local_compose = Path("/workspace/docker-compose.local.yml").read_text(encoding="utf-8")
    prod_alloy = Path("/workspace/infrastructure/observability/alloy.prod.alloy")
    local_alloy = Path("/workspace/infrastructure/observability/alloy.local.alloy")

    assert prod_alloy.exists()
    assert local_alloy.exists()

    prod_alloy_content = prod_alloy.read_text(encoding="utf-8")
    local_alloy_content = local_alloy.read_text(encoding="utf-8")

    assert 'alloy:' in prod_compose
    assert 'alloy:' in local_compose
    assert 'OTEL_EXPORTER_OTLP_ENDPOINT: ${OTEL_EXPORTER_OTLP_ENDPOINT:-http://alloy:4318}' in prod_compose
    assert 'OTEL_EXPORTER_OTLP_ENDPOINT: ${OTEL_EXPORTER_OTLP_ENDPOINT:-http://alloy:4318}' in local_compose
    assert 'OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf' in prod_compose
    assert 'OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf' in local_compose
    assert 'otelcol.receiver.otlp "default"' in prod_alloy_content
    assert 'otelcol.connector.spanmetrics "default"' in prod_alloy_content
    assert 'otelcol.connector.servicegraph "default"' in prod_alloy_content
    assert 'otelcol.exporter.debug "default"' in local_alloy_content
