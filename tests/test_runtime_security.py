from pathlib import Path


def test_runtime_security_baseline_is_hardened_in_compose_and_kubernetes() -> None:
    prod_compose = Path("/workspace/docker-compose.yml").read_text(encoding="utf-8")
    local_compose = Path("/workspace/docker-compose.local.yml").read_text(encoding="utf-8")
    namespace_yaml = Path("/workspace/k8s/apps/zeroclaw-assistant/namespace.yaml").read_text(
        encoding="utf-8"
    )
    kustomization_yaml = Path("/workspace/k8s/apps/zeroclaw-assistant/kustomization.yaml").read_text(
        encoding="utf-8"
    )
    network_policy = Path("/workspace/k8s/apps/zeroclaw-assistant/networkpolicy.yaml")

    assert "pids_limit: 256" in prod_compose
    assert "pids_limit: 256" in local_compose
    assert 'pod-security.kubernetes.io/enforce: restricted' in namespace_yaml
    assert 'pod-security.kubernetes.io/audit: restricted' in namespace_yaml
    assert 'pod-security.kubernetes.io/warn: restricted' in namespace_yaml
    assert network_policy.exists()
    assert "- networkpolicy.yaml" in kustomization_yaml

    network_policy_content = network_policy.read_text(encoding="utf-8")
    assert "kind: NetworkPolicy" in network_policy_content
    assert "policyTypes:" in network_policy_content
    assert "- Ingress" in network_policy_content
    assert "- Egress" in network_policy_content
    assert "ingress: []" in network_policy_content
    assert 'port: 53' in network_policy_content
    assert 'port: 443' in network_policy_content
