"""Интерфейс получения экземпляра."""

from simple_logs_sender import cfg
from simple_logs_sender.plugins.dummy.main import DummyPlugin


def get_plugin(global_config: cfg.Config, tag: str) -> DummyPlugin:
    """Вернуть экземпляр плагина."""
    return DummyPlugin(global_config, tag)
