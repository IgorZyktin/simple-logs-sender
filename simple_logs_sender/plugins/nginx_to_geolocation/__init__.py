"""Интерфейс получения экземпляра."""

import nano_settings as ns

from simple_logs_sender import cfg
from simple_logs_sender.plugins.nginx_to_geolocation import local_cfg
from simple_logs_sender.plugins.nginx_to_geolocation.main import NginxToGeolocationPlugin


def get_plugin(global_config: cfg.Config, tag: str) -> NginxToGeolocationPlugin:
    """Вернуть экземпляр плагина."""
    config = ns.from_env(local_cfg.PostgresqlConfig, env_prefix='SLS__POSTGRESQL')
    return NginxToGeolocationPlugin(
        global_config=global_config,
        config=config,
        tag=tag,
    )
