"""Plugin discovery + enabled-state management.

Discovers installed markitdown plugins via the standard
`importlib.metadata` entry-point group `markitdown.plugin`. Each
discovered plugin is mapped to a `PluginInfo` describing its package,
version, and enabled/disabled state (kept in AppConfig.enabled_plugins).
"""

from __future__ import annotations

from importlib import metadata as importlib_metadata

from ..models.config import AppConfig
from ..models.plugin_info import PluginInfo


_PLUGIN_GROUP = "markitdown.plugin"


def list_installed_plugins(cfg: AppConfig) -> list[PluginInfo]:
    """Enumerate all markitdown-plugin entry points.

    Empty list if no plugins are installed. Each entry's `dist` metadata
    is consulted for version + distribution name; falls back to "unknown"
    if unavailable.
    """
    try:
        eps = importlib_metadata.entry_points(group=_PLUGIN_GROUP)
    except Exception:
        return []

    # Python 3.10+ returns a `selectable` view; coerce to list for safety.
    eps = list(eps)

    # Build a lookup: module -> dist (for version + package name)
    by_module: dict[str, importlib_metadata.Distribution] = {}
    for dist in importlib_metadata.distributions():
        for ep in dist.entry_points:
            if ep.group == _PLUGIN_GROUP:
                # Top-level module name (e.g. "markitdown_ocr" from "markitdown_ocr.__init__")
                top = ep.module.split(".")[0] if ep.module else ep.name
                by_module[top] = dist

    enabled_set = set(cfg.enabled_plugins)
    result: list[PluginInfo] = []
    for ep in eps:
        top = ep.module.split(".")[0] if ep.module else ep.name
        dist = by_module.get(top)
        version = "unknown"
        distribution = "unknown"
        if dist is not None:
            try:
                version = dist.metadata["Version"] or "unknown"
            except Exception:
                pass
            distribution = dist.metadata["Name"] or dist.name or "unknown"
        # loaded: in this design, "loaded" means entry point is on disk.
        # Whether MarkItDown's _load_plugins() can import it without error
        # is checked at build_markitdown time, not here.
        loaded = True
        # enabled: an empty allowlist means "all enabled"; otherwise
        # membership in the set determines it.
        enabled = (not enabled_set) or (top in enabled_set)
        result.append(
            PluginInfo(
                name=ep.name,
                module=top,
                version=version,
                distribution=distribution,
                loaded=loaded,
                enabled=enabled,
            )
        )
    return sorted(result, key=lambda p: p.name)


def set_plugin_enabled(plugin: PluginInfo, enabled: bool, cfg: AppConfig) -> AppConfig:
    """Return a new AppConfig with the given plugin's enabled-state updated.

    An empty enabled_plugins list means "all loaded plugins are enabled";
    the moment we toggle anything explicitly, we materialize the full
    list and patch the one entry.
    """
    current = set(cfg.enabled_plugins)
    if not current:
        # Materialize: assume all currently-loaded plugins are now explicit
        all_plugins = [p.module for p in list_installed_plugins(cfg)]
        current = set(all_plugins)
    if enabled:
        current.add(plugin.module)
    else:
        current.discard(plugin.module)
    return AppConfig.from_dict(
        {**cfg.to_dict(), "enabled_plugins": sorted(current)}
    )
