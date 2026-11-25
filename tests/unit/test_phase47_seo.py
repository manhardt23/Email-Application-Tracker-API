"""Phase 47 — the tracker is an app page, not a personal-name result."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "frontend" / "index.html"
ROBOTS = ROOT / "frontend" / "public" / "robots.txt"
SITEMAP = ROOT / "frontend" / "public" / "sitemap.xml"
NGINX = ROOT / "nginx" / "conf.d" / "tracker.conf"

CANONICAL = "https://jemanhardt.dev/"
DESCRIPTION = (
    "Application Tracker is a private dashboard for job applications, "
    "related email, and pipeline status."
)


def test_public_html_identifies_the_app_not_a_person():
    html = INDEX.read_text()
    assert "<title>Application Tracker</title>" in html
    assert f'<meta\n      name="description"\n      content="{DESCRIPTION}"' in html
    assert f'<link rel="canonical" href="{CANONICAL}" />' in html
    assert '<meta property="og:site_name" content="Application Tracker" />' in html
    assert '<meta property="og:title" content="Application Tracker" />' in html
    assert f'<meta\n      property="og:description"\n      content="{DESCRIPTION}"' in html
    assert '<meta property="og:type" content="website" />' in html
    assert f'<meta property="og:url" content="{CANONICAL}" />' in html
    assert '<meta name="twitter:card" content="summary" />' in html
    assert '<meta name="twitter:title" content="Application Tracker" />' in html
    assert f'<meta\n      name="twitter:description"\n      content="{DESCRIPTION}"' in html
    assert '"@type": "WebApplication"' in html
    assert '"name": "Application Tracker"' in html
    assert f'"url": "{CANONICAL}"' in html
    lowered = html.lower()
    assert "jacob manhardt" not in lowered
    assert "linkedin" not in lowered
    assert "og:image" not in lowered
    assert "twitter:image" not in lowered
    assert "schema.org/person" not in lowered
    assert '"@type": "person"' not in lowered


def test_robots_and_sitemap_use_the_current_host():
    robots = ROBOTS.read_text()
    sitemap = SITEMAP.read_text()
    assert "Sitemap: https://jemanhardt.dev/sitemap.xml" in robots
    assert "Disallow: /mcp" in robots
    assert "Allow: /" in robots
    assert "<loc>https://jemanhardt.dev/</loc>" in sitemap
    combined = (robots + sitemap).lower()
    assert "jacob" not in combined
    assert "linkedin" not in combined


def test_seo_does_not_retarget_the_host_or_mcp_path():
    nginx = NGINX.read_text()
    assert "server_name jemanhardt.dev www.jemanhardt.dev tracker.jemanhardt.dev;" in nginx
    assert "location /mcp {" in nginx
