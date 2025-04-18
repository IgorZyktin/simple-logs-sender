"""Интерфейс получения экземпляра."""

import nano_settings as ns

from simple_logs_sender import cfg
from simple_logs_sender.plugins.nginx_to_postgres import local_cfg
from simple_logs_sender.plugins.nginx_to_postgres.main import NginxToPostgresqlPlugin


def get_plugin(global_config: cfg.Config, tag: str) -> NginxToPostgresqlPlugin:
    """Вернуть экземпляр плагина."""
    config = ns.from_env(local_cfg.PostgresqlConfig, env_prefix='SLS__POSTGRESQL')
    return NginxToPostgresqlPlugin(
        global_config=global_config,
        config=config,
        tag=tag,
    )
