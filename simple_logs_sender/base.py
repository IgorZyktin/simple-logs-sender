"""Описание базовых инструментов."""

import abc
from typing import TypedDict

from simple_logs_sender import cfg


class Payload(TypedDict):
    """Формат данных от сервера."""

    registered_at: str
    tag: str
    message: str


class Plugin(abc.ABC):
    """Базовый вариант плагина."""

    name: str = 'base'

    def __init__(self, global_config: cfg.Config, tag: str) -> None:
        """Инициализировать экземпляр."""
        self.global_config = global_config
        self.tag = tag
        self.running = None

    async def start(self) -> None:
        """Подготовить плагин к работе."""
        self.running = True

    @abc.abstractmethod
    async def process(self, payload: Payload) -> None:
        """Обработать запрос."""

    async def stop(self) -> None:
        """Бережно остановить плагин."""
        self.running = False
