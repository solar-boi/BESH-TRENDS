"""Regression tests for package discovery and imports."""

import importlib


def test_dart_package_submodules_import_cleanly():
    modules = [
        "dart",
        "dart.api",
        "dart.api.comed_client",
        "dart.config",
        "dart.config.settings",
        "dart.models",
        "dart.services",
        "dart.utils",
        "dart.visualization",
    ]

    for module_name in modules:
        assert importlib.import_module(module_name) is not None
