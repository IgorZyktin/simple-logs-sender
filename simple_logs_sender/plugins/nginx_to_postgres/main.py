"""Плагин для пересылки логов в PostgreSQL."""

import logging

import iso8601
import ujson
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
import sqlalchemy as sa

from simple_logs_sender import base
from simple_logs_sender import cfg
from simple_logs_sender.plugins.nginx_to_postgres import local_cfg

LOG = logging.getLogger(__name__)

Base = declarative_base()


class Logs(Base):
    """Хранилище логов."""

    __tablename__ = 'nginx_logs'

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True, index=True)
    hostname = sa.Column(sa.String(255), nullable=False, index=True)
    ip = sa.Column(sa.String(15), nullable=False)
    path = sa.Column(sa.String(1024), nullable=False)
    time = sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    user_agent = sa.Column(sa.String(255), nullable=True)
    user_id_got = sa.Column(sa.String(255), nullable=True)
    user_id_set = sa.Column(sa.String(255), nullable=True)
    remote_user = sa.Column(sa.String(255), nullable=True)
    request = sa.Column(sa.String(255), nullable=True)
    method = sa.Column(sa.String(16), nullable=False)
    status = sa.Column(sa.Integer, nullable=False, index=True)
    body_bytes_sent = sa.Column(sa.Integer, nullable=False)
    request_time = sa.Column(sa.Float, nullable=False)
    http_referrer = sa.Column(sa.String(255), nullable=True)


def maybe_str(string: str) -> str | None:
    """Попытаться преобразовать в нормальную строку."""
    return string if string != '-' else None


class NginxToPostgresqlPlugin(base.Plugin):
    """Плагин для пересылки логов в PostgreSQL."""

    name: str = 'nginx_to_postgresql'

    def __init__(
        self,
        global_config: cfg.Config,
        config: local_cfg.PostgresqlConfig,
        tag: str,
    ) -> None:
        """Инициализировать экземпляр."""
        super().__init__(global_config, tag)
        self.config = config
        self._engine = create_async_engine(
            url=self.config.db_url,
            echo=False,
            pool_pre_ping=True,
        )

    async def start(self) -> None:
        """Подготовить плагин к работе."""
        await super().start()

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        LOG.info('Nginx -> PostgreSQL plugin started')

    async def process(self, payload: base.Payload) -> None:
        """Обработать запрос.

        Пример сырого сообщения:
        {
            'timestamp': '2025-02-24T22:46:30.596767+03:00',
            'tag': 'sls-nginx',
            'hostname': 'my-host',
            'message': '{"path": "/",
                        "ip": "46.19.143.26",
                        "time": "2025-02-24T22:46:30+03:00",
                        "user_agent": "-",
                        "user_id_got": "-",
                        "user_id_set": "-",
                        "remote_user": "-",
                        "request": "GET / HTTP/1.1",
                        "status": "200",
                        "body_bytes_sent": "615",
                        "request_time": "0.000",
                        "http_referrer": "-"}'
        }
        """
        message = ujson.loads(payload['message'])

        values = {
            'hostname': payload['hostname'],
            'ip': message['ip'],
            'path': message['path'],
            'time': iso8601.parse_date(message['time']),
            'user_agent': maybe_str(message['user_agent']),
            'user_id_got': maybe_str(message['user_id_got']),
            'user_id_set': maybe_str(message['user_id_set']),
            'remote_user': maybe_str(message['remote_user']),
            'request': message['request'],
            'method': str(message['request']).split(' ', maxsplit=1)[0],
            'status': int(message['status']),
            'body_bytes_sent': int(message['body_bytes_sent']),
            'request_time': float(message['request_time']),
            'http_referrer': maybe_str(message['http_referrer']),
        }

        try:
            async with self._engine.begin() as conn:
                stmt = sa.insert(Logs).values(**values)
                await conn.execute(stmt)
        except TimeoutError as exc:
            LOG.exception(
                'Failed to save record to the database, '
                'error: %s, record: %s',
                exc,
                values,
            )

    async def stop(self) -> None:
        """Бережно остановить плагин."""
        await super().stop()
        await self._engine.dispose()
        LOG.info('Nginx -> PostgreSQL plugin stopped')
