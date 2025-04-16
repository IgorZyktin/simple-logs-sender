"""Конфигурация плагина."""

from dataclasses import dataclass

import nano_settings as ns


@dataclass
class PostgresqlConfig(ns.BaseConfig):
    """Конфигурация плагина."""

    db_url: str
