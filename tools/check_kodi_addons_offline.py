#!/usr/bin/env python3
"""Run Team Kodi's checker without its rate-limited repository download.

The official checker normally downloads every historical Kodi repository even
when dependency checks are disabled. That mirror frequently returns HTTP 429.
This wrapper keeps all local schema, artwork, file, language and code checks,
while deliberately omitting only official-repository dependency/version lookup.
"""
from types import SimpleNamespace

from kodi_addon_checker import ValidKodiVersions, check_addon
from kodi_addon_checker.common import load_plugins
from kodi_addon_checker.config import Config
from kodi_addon_checker.reporter import ReportManager


class EmptyRepository:
    def __contains__(self, key):
        return False

    def find(self, key):
        return None

    def rdepends(self, key):
        return []


def main():
    load_plugins()
    ReportManager.enable(["console"])
    args = SimpleNamespace(
        branch="omega", allow_folder_id_mismatch=False, skip_dependency_checks=True,
        PR=False, reporter=["console"], max_entrypoint_count=15,
        check_license_file_exists=True, check_kodi_leia_deprecations=True,
    )
    repositories = {name: EmptyRepository() for name in ValidKodiVersions}
    problems = 0
    for path in ("plugin.video.dinotv", "repository.dinotv"):
        report = check_addon.start(path, args, repositories, Config(path, args))
        problems += report.problem_count
        print("{}: {} problem(s), {} warning(s)".format(path, report.problem_count, report.warning_count))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
