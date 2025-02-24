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
        chunk_size: int,
        plugins: dict[str, list[base.Plugin]],
        logger: logging.Logger,
    ) -> None:
        """Инициализировать экземпляр."""
        self.host = host
        self.port = port
        self.chunk_size = chunk_size
        self.plugins = plugins
        self.server = None
        self.logger = logger
        self._tasks: set = set()

    async def handle_client(self, reader, writer):
        """Начать обрабатывать входящее соединение."""
        while True:
            try:
                # по всей видимости rsyslog не оповещает о конце передачи,
                # вариант <читать в цикле, пока не получим b''> не работает
                raw_data = await reader.read(self.chunk_size)

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
