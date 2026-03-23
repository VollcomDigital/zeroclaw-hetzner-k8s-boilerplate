"""Regression: OTLP exporter when OTEL_EXPORTER_OTLP_ENDPOINT is set."""

from __future__ import annotations

import pytest
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

import n8n_bridge.server as server


def test_span_exporter_is_otlp_when_endpoint_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://alloy:4318")
    exporter = server._span_exporter_from_env()
    assert isinstance(exporter, OTLPSpanExporter)


def test_span_exporter_is_console_when_endpoint_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    exporter = server._span_exporter_from_env()
    assert isinstance(exporter, ConsoleSpanExporter)


def test_span_exporter_is_console_when_endpoint_whitespace_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "  \t  ")
    exporter = server._span_exporter_from_env()
    assert isinstance(exporter, ConsoleSpanExporter)
