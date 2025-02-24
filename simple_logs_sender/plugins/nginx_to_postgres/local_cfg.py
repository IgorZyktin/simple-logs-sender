"""Конфигурация плагина."""

from dataclasses import dataclass

from simple_logs_sender.cfg import BaseConfig


@dataclass
class PostgresqlConfig(BaseConfig):
    """Конфигурация плагина."""

    db_url: str
