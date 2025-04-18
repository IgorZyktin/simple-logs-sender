"""Плагин-пустышка, подходит для проверки работы."""

import logging
from typing import Any

from simple_logs_sender import base

LOG = logging.getLogger(__name__)


class DummyPlugin(base.Plugin):
    """Плагин-пустышка, подходит для проверки работы."""

    name: str = 'dummy'

    async def start(self, global_variables: dict[str, Any]) -> None:
        """Подготовить плагин к работе."""
        LOG.info('Dummy plugin started')

    async def process(self, payload: base.Payload) -> None:
        """Обработать запрос."""
        LOG.info('Dummy processing %s', payload)

    async def stop(self) -> None:
        """Бережно остановить плагин."""
        LOG.info('Dummy plugin stopped')
