"""Конфигурация плагина."""

from dataclasses import dataclass

import python_utilz as pu


@dataclass
class PostgresqlConfig(pu.BaseConfig):
    """Конфигурация плагина."""

    db_url: str
