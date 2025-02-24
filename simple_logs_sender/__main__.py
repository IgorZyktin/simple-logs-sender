"""Простое приложение, которое перенаправляет логи в другие места."""

import asyncio
from collections import defaultdict
import importlib
import logging
import os
from pathlib import Path
import signal
import sys

from simple_logs_sender import base
from simple_logs_sender import cfg
from simple_logs_sender import transport


async def main():
    """Точка входа."""
    config = cfg.from_env(cfg.Config)
    logger = get_logger(config)

    add_signal_handlers(logger)

    server = None
    plugins: dict[str, list[base.Plugin]] = {}

    try:
        logger.info('Simple logs sender starting')
        server, plugins = get_server_and_plugins(config, logger)
        await start_all(server, plugins, logger)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    except Exception:
        logger.exception('Failed to start simple logs sender')
        sys.exit(1)
    finally:
        await stop_all(server, plugins, logger)

    logger.info('Simple logs sender stopped')


async def start_all(
    server: transport.TCPServer,
    plugins: dict[str, list[base.Plugin]],
    logger: logging.Logger,
) -> None:
    """Включить работу всех компонентов."""
    already_started: set[str] = set()

    for nested_plugins in plugins.values():
        for plugin in nested_plugins:
            if plugin.name in already_started:
                continue

            try:
                await plugin.start()
            except Exception:
                logger.exception('Failed to start plugin %r', plugin.name)
            finally:
                already_started.add(plugin.name)

    await server.start_server()


async def stop_all(
    server: transport.TCPServer | None,
    plugins: dict[str, list[base.Plugin]],
    logger: logging.Logger,
) -> None:
    """Остановить работу всех компонентов."""
    already_stopped: set[str] = set()

    for nested_plugins in plugins.values():
        for plugin in nested_plugins:
            if plugin.name in already_stopped:
                continue

            try:
                await plugin.stop()
            except Exception:
                logger.exception('Failed to stop plugin %r', plugin.name)
            finally:
                already_stopped.add(plugin.name)

    if server is not None:
        try:
            await server.stop_server()
        except Exception:
            logger.exception('Failed to stop TCP server')
            sys.exit(1)


def add_signal_handlers(logger: logging.Logger) -> None:
    """Добавить обработки сигналов (нужно для перезагрузки)."""
    if os.name == 'nt':
        logger.warning('Running on Windows, can stop only using Ctr+C')
        return

    loop = asyncio.get_event_loop()

    async def shutdown(sig: signal.Signals) -> None:
        """Остановить все задачи в исполнении (кроме этой)."""
        logger.warning('Caught signal %s', sig.name)
        try:
            tasks = []
            for task in asyncio.all_tasks(loop):
                if task is not asyncio.current_task(loop):
                    task.cancel()
                    tasks.append(task)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.info('Finished awaiting cancelled tasks, results: %s', results)
        finally:
            loop.stop()

    for each in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(each, lambda _sig=each: asyncio.create_task(shutdown(_sig)))


def get_logger(config: cfg.Config) -> logging.Logger:
    """Настроить и вернуть логгер.

    Мы можем настраивать файл для логирования, поэтому надо,
    чтобы logging.getLogger всегда вызывался после logging.basicConfig.
    """
    kwargs = {}

    if config.log_file:
        kwargs['filename'] = config.log_file

    logging.basicConfig(
        level=logging.INFO,
        format=config.log_format,
        **kwargs,
    )

    logger = logging.getLogger(__name__)
    return logger


def get_server_and_plugins(
    config: cfg.Config,
    logger: logging.Logger,
) -> tuple[transport.TCPServer, dict[str, list[base.Plugin]]]:
    """Настроить и вернуть базовые компоненты - сервер и роутер."""
    plugins = get_plugins(config, logger)

    server = transport.TCPServer(
        host=config.host,
        port=config.port,
        chunk_size=config.chunk_size,
        plugins=plugins,
        logger=logger,
    )

    return server, plugins


def get_plugins(config: cfg.Config, logger: logging.Logger) -> dict[str, list[base.Plugin]]:
    """Импортировать и вернуть все плагины."""
    plugins: dict[str, list[base.Plugin]] = defaultdict(list)
    all_plugins: set[str] = set()
    local = Path('.') / config.plugins_path

    logger.info('Getting plugins from %s', local.absolute())

    for tag, plugin_names in config.plugins.items():
        for name in plugin_names:
            path = local / name.lower()

            if not path.exists() or path.name.startswith('_'):
                continue

            try:
                module = importlib.import_module(f'plugins.{name.lower()}')
                plugin = module.get_plugin(config, tag)
                plugins[plugin.tag].append(plugin)
            except Exception:
                logger.exception('Failed to import plugin %r', name)
            else:
                all_plugins.add(plugin.name)

    logger.info('Starting with plugins: %s', sorted(all_plugins))

    return plugins


if __name__ == '__main__':
    asyncio.run(main())
