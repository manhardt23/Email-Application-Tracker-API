"""The origin 502 survived a green deploy because two nginx files claimed the same name."""

from pathlib import Path

CONF_DIR = Path("nginx/conf.d")
WORKFLOW = Path(".github/workflows/ci.yml")


def test_only_tracker_conf_is_loaded_and_reresolves_api():
    confs = sorted(path.name for path in CONF_DIR.glob("*.conf"))
    assert confs == ["tracker.conf"]
    text = (CONF_DIR / "tracker.conf").read_text()
    assert "resolver 127.0.0.11 valid=10s ipv6=off;" in text
    assert "set $api_backend api:8000;" in text
    assert "proxy_pass http://$api_backend;" in text
    assert "server_name jemanhardt.dev www.jemanhardt.dev;" in text
    assert "proxy_pass http://api:8000;" not in text


def test_deploy_overwrites_host_conf_and_fails_when_api_is_unhealthy():
    workflow = WORKFLOW.read_text()
    assert workflow.count("overwrite: true") >= 2
    assert "find nginx/conf.d -maxdepth 1 -type f ! -name tracker.conf -delete" in workflow
    assert "logs --tail=200 api" in workflow
    assert "--force-recreate nginx" in workflow
    compose = Path("docker-compose.prod.yml").read_text()
    assert "service_healthy" in compose
    assert "/api/v1/health" in compose
