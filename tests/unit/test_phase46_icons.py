"""Favicon, manifest, and logo structured data stay on the existing site name."""

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "frontend" / "public"
INDEX = ROOT / "frontend" / "index.html"

PNG_SIZES = {
    "favicon-16x16.png": (16, 16),
    "favicon-32x32.png": (32, 32),
    "favicon-48x48.png": (48, 48),
    "apple-touch-icon.png": (180, 180),
    "brand/icon-192.png": (192, 192),
    "brand/logo.png": (512, 512),
}


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _json_ld() -> dict:
    html = INDEX.read_text()
    start = html.index('type="application/ld+json">') + len('type="application/ld+json">')
    end = html.index("</script>", start)
    return json.loads(html[start:end])


def test_homepage_keeps_its_title_and_points_at_the_icons():
    html = INDEX.read_text()
    assert "<title>Email Application Tracker</title>" in html
    assert html.count("<title>") == 1
    for href in (
        "/favicon.ico",
        "/favicon-16x16.png",
        "/favicon-32x32.png",
        "/favicon-48x48.png",
        "/apple-touch-icon.png",
        "/site.webmanifest",
    ):
        assert f'href="{href}"' in html


def test_structured_data_is_the_site_name_url_and_logo_only():
    graph = _json_ld()["@graph"]
    organization = next(node for node in graph if node["@type"] == "Organization")
    website = next(node for node in graph if node["@type"] == "WebSite")

    assert organization["name"] == "Email Application Tracker"
    assert organization["url"] == "https://jemanhardt.dev/"
    assert organization["logo"]["url"] == "https://jemanhardt.dev/brand/logo.png"
    assert organization["logo"]["width"] == 512
    assert organization["logo"]["height"] == 512
    assert set(organization) == {"@type", "@id", "name", "url", "logo"}

    assert website["name"] == "Email Application Tracker"
    assert website["url"] == "https://jemanhardt.dev/"
    assert website["publisher"] == {"@id": "https://jemanhardt.dev/#organization"}
    assert set(website) == {"@type", "@id", "name", "url", "publisher"}


def test_manifest_lists_the_icon_files():
    manifest = json.loads((PUBLIC / "site.webmanifest").read_text())
    assert manifest["name"] == "Email Application Tracker"
    assert manifest["short_name"] == "App Tracker"
    icons = {icon["sizes"]: icon["src"] for icon in manifest["icons"]}
    assert icons["16x16"] == "/favicon-16x16.png"
    assert icons["32x32"] == "/favicon-32x32.png"
    assert icons["48x48"] == "/favicon-48x48.png"
    assert icons["180x180"] == "/apple-touch-icon.png"
    assert icons["192x192"] == "/brand/icon-192.png"
    assert icons["512x512"] == "/brand/logo.png"


def test_icon_files_exist_at_the_linked_sizes():
    for name, size in PNG_SIZES.items():
        assert _png_size(PUBLIC / name) == size

    ico = (PUBLIC / "favicon.ico").read_bytes()
    assert ico[:4] == b"\x00\x00\x01\x00"
    count = struct.unpack_from("<H", ico, 4)[0]
    assert count == 3
    widths = []
    for index in range(count):
        entry = 6 + index * 16
        width = ico[entry] or 256
        height = ico[entry + 1] or 256
        widths.append((width, height))
    assert set(widths) == {(16, 16), (32, 32), (48, 48)}

    source = (PUBLIC / "brand" / "logo.svg").read_text()
    assert "Placeholder mark" in source
    assert "Replace" in source
    assert 'fill="#1c1917"' in source
