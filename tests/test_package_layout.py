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
        "dart.services.pricing_calculations",
        "dart.services.pricing_service",
        "dart.utils",
        "dart.utils.helpers",
        "dart.utils.analytics",
        "dart.utils.pricing_audit_logger",
        "dart.utils.share_links",
        "dart.utils.logger_util",
        "dart.visualization",
        "dart.visualization.formatting",
        "dart.visualization.charts",
        "dart.visualization.data_layer",
        "dart.visualization.ui_helpers",
        "dart.visualization.sections",
        "dart.visualization.sections.sidebar",
        "dart.visualization.sections.header",
        "dart.visualization.sections.live_snapshot",
        "dart.visualization.sections.recent_prices",
        "dart.visualization.sections.custom_range",
    ]

    for module_name in modules:
        assert importlib.import_module(module_name) is not None
