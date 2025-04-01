"""Простой TCP сервер, который получает данные от rsyslog."""

import asyncio
import json
import logging
import sys

import ujson

from simple_logs_sender import base


class TCPServer:
    """Простой TCP сервер, который получает данные от rsyslog."""

    def __init__(
        self,
        host: str,
        port: int,
        plugins: dict[str, list[base.Plugin]],
        logger: logging.Logger,
        *,
        verbose: bool,
    ) -> None:
        """Инициализировать экземпляр."""
        self.host = host
        self.port = port
        self.plugins = plugins
        self.server = None
        self.logger = logger
        self.verbose = verbose
        self._tasks: set = set()

    async def handle_client(self, reader, writer):
        """Начать обрабатывать входящее соединение."""
        while True:
            try:
                raw_data = await reader.readline()

                if not raw_data:
                    break

                try:
                    payload = base.Payload(**ujson.loads(raw_data))
                except (TypeError, ValueError, json.JSONDecodeError):
                    self.logger.error('Failed to parse JSON: %r', raw_data)
                    continue

                tag = payload.get('tag')

                if tag is None:
                    self.logger.error('Incorrect payload structure: %r', raw_data)
                    continue

                if self.verbose:
                    self.logger.info('Got message from %(hostname)s with tag %(tag)s', payload)

                actual_plugins = self.plugins.get(tag)

                if actual_plugins is not None:
                    for plugin in actual_plugins:
                        task = asyncio.create_task(plugin.process(payload))
                        self._tasks.add(task)
                        task.add_done_callback(lambda _task: self._tasks.discard(_task))

            except Exception:
                self.logger.exception('Error processing request')
                break

        writer.close()
        await writer.wait_closed()

    async def start_server(self):
        """Запустить TCP сервер."""
        try:
            self.server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port,
            )

            self.logger.info('TCP server started on %s:%s', self.host, self.port)

            async with self.server:
                await self.server.serve_forever()
        except Exception:
            self.logger.exception('Error starting TCP server')
            sys.exit(1)

    async def stop_server(self):
        """Остановить TCP сервер."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        self.logger.info('TCP server stopped')
