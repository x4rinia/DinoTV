#!/usr/bin/env python3
"""Build a deterministic Kodi repository tree from the two source add-ons."""

import argparse
import hashlib
import os
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ADDON_IDS = ("repository.dinotv", "plugin.video.dinotv")


def read_addon(addon_dir):
    path = addon_dir / "addon.xml"
    root = ET.parse(path).getroot()
    if root.tag != "addon" or root.attrib.get("id") != addon_dir.name:
        raise ValueError("Ungültige Add-on-ID in {}".format(path))
    version = root.attrib.get("version", "")
    if not version or version.count(".") < 2:
        raise ValueError("Ungültige Version in {}".format(path))
    return root, version


def zip_addon(addon_dir, destination, version):
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "{}-{}.zip".format(addon_dir.name, version)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for path in sorted(addon_dir.rglob("*")):
            if path.is_dir() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            relative = Path(addon_dir.name) / path.relative_to(addon_dir)
            info = zipfile.ZipInfo(str(relative).replace(os.sep, "/"), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            handle.writestr(info, path.read_bytes())
    return archive


def build(output):
    output = Path(output).resolve()
    if output == ROOT or ROOT not in output.parents:
        raise ValueError("Ausgabe muss innerhalb des DinoTV-Workspace liegen")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    addon_roots = []
    archives = []
    for addon_id in ADDON_IDS:
        source = ROOT / addon_id
        root, version = read_addon(source)
        addon_roots.append(root)
        destination = output / addon_id
        archive = zip_addon(source, destination, version)
        archives.append(archive)
        for name in ("icon.png", "fanart.jpg"):
            candidates = (source / name, source / "resources" / name)
            asset = next((item for item in candidates if item.exists()), None)
            if asset:
                shutil.copy2(asset, destination / name)
        (destination / "changelog-{}.txt".format(version)).write_text(
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
        )
    document = ET.Element("addons")
    for root in addon_roots:
        document.append(root)
    ET.indent(document, space="  ")
    xml_bytes = ET.tostring(document, encoding="utf-8", xml_declaration=True)
    addons_xml = output / "addons.xml"
    addons_xml.write_bytes(xml_bytes + b"\n")
    digest = hashlib.md5(addons_xml.read_bytes()).hexdigest()  # Kodi repository protocol requires this legacy filename/value.
    (output / "addons.xml.md5").write_text(digest + "\n", encoding="ascii", newline="\n")
    return archives


def write_site_index(site_root, archives):
    links = "\n".join(
        '<li><a href="addons/{0}/{1}">{1}</a></li>'.format(path.parent.name, path.name) for path in archives
    )
    html = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>DinoTV Kodi Repository</title><style>body{{max-width:760px;margin:3rem auto;padding:1rem;background:#061421;color:#eafaff;font:18px system-ui}}a{{color:#23d5dc}}code{{color:#7edcff}}</style></head>
<body><h1>DinoTV</h1><p>Kodi-Repository für American Football.</p><h2>Downloads</h2><ul>{}</ul>
<p>Installiere zuerst <code>repository.dinotv</code> als ZIP in Kodi.</p><p><a href="https://github.com/x4rinia/DinoTV">Quellcode und Anleitung</a></p></body></html>
""".format(links)
    site_root.mkdir(parents=True, exist_ok=True)
    (site_root / "index.html").write_text(html, encoding="utf-8", newline="\n")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "addons"))
    parser.add_argument("--site-root", default="")
    args = parser.parse_args(argv)
    archives = build(args.output)
    if args.site_root:
        write_site_index(Path(args.site_root).resolve(), archives)
    for archive in archives:
        print(archive)
    return 0


if __name__ == "__main__":
    sys.exit(main())
