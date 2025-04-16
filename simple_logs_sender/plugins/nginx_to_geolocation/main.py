"""Плагин для получения геолокации и пересылки в PostgreSQL."""

import logging
from typing import Any

import aiohttp
import iso8601
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import declarative_base
import ujson

from simple_logs_sender import base
from simple_logs_sender import cfg
from simple_logs_sender.plugins.nginx_to_geolocation import local_cfg

LOG = logging.getLogger(__name__)

Base = declarative_base()


class IpGeolocation(Base):
    """Хранилище логов."""

    __tablename__ = 'ip_geolocation'

    ip = sa.Column(sa.String(15), nullable=False, index=True, primary_key=True)
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False)
    country = sa.Column(sa.String(255))
    country_code = sa.Column(sa.String(255))
    region = sa.Column(sa.String(255))
    region_name = sa.Column(sa.String(255))
    city = sa.Column(sa.String(255))
    zip = sa.Column(sa.String(255))
    lat = sa.Column(sa.Float())
    lon = sa.Column(sa.Float())
    ip_timezone = sa.Column(sa.String(255))
    isp = sa.Column(sa.String(255))
    org = sa.Column(sa.String(255))
    org_as = sa.Column(sa.String(255))


class NginxToGeolocationPlugin(base.Plugin):
    """Плагин для получения геолокации и пересылки в PostgreSQL."""

    name: str = 'nginx_to_geolocation'

    def __init__(
        self,
        global_config: cfg.Config,
        config: local_cfg.PostgresqlConfig,
        tag: str,
    ) -> None:
        """Инициализировать экземпляр."""
        super().__init__(global_config, tag)
        self.config = config
        self._already_added: set[str] = set()
        self.global_variables: dict[str, Any] = {}

    async def start(self, global_variables: dict[str, Any]) -> None:
        """Подготовить плагин к работе."""
        self.global_variables = global_variables
        LOG.info('Nginx -> PostgreSQL geolocation plugin started')

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

        Пример ответа API:
        {
            "query": "24.48.0.1",
            "status": "success",
            "country": "Canada",
            "countryCode": "CA",
            "region": "QC",
            "regionName": "Quebec",
            "city": "Montreal",
            "zip": "H1K",
            "lat": 45.6085,
            "lon": -73.5493,
            "timezone": "America/Toronto",
            "isp": "Le Groupe Videotron Ltee",
            "org": "Videotron Ltee",
            "as": "AS5769 Videotron Ltee"
        }
        """
        engine = self.global_variables.get('engine')

        if engine is None:
            LOG.error('Got no engine for %s', self.name)
            return

        message = ujson.loads(payload['message'])
        ip = message['ip']

        if ip in self._already_added:
            return

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(f'http://ip-api.com/json/{ip}', timeout=1.0) as resp,
            ):
                geolocation = await resp.json()
        except Exception as exc:
            LOG.exception(
                'Failed to get geolocation for IP %s: %s',
                ip,
                exc,  # noqa: TRY401
            )
            return

        try:
            values = {
                'ip': ip,
                'updated_at': iso8601.parse_date(message['time']),
                'country': geolocation['country'],
                'country_code': geolocation['countryCode'],
                'region': geolocation['region'],
                'region_name': geolocation['regionName'],
                'city': geolocation['city'],
                'zip': geolocation['zip'],
                'lat': geolocation['lat'],
                'lon': geolocation['lon'],
                'ip_timezone': geolocation['timezone'],
                'isp': geolocation['isp'],
                'org': geolocation['org'],
                'org_as': geolocation['as'],
            }
        except Exception as exc:
            LOG.exception(
                'Failed to parse API response: %s',
                exc,  # noqa: TRY401
            )
            return

        try:
            insert = pg_insert(IpGeolocation).values(**values)

            stmt = insert.on_conflict_do_update(
                index_elements=[IpGeolocation.ip],
                set_={
                    'updated_at': insert.excluded.updated_at,
                    'country': insert.excluded.country,
                    'country_code': insert.excluded.country_code,
                    'region': insert.excluded.region,
                    'region_name': insert.excluded.region_name,
                    'city': insert.excluded.city,
                    'zip': insert.excluded.zip,
                    'lat': insert.excluded.lat,
                    'lon': insert.excluded.lon,
                    'ip_timezone': insert.excluded.ip_timezone,
                    'isp': insert.excluded.isp,
                    'org': insert.excluded.org,
                    'org_as': insert.excluded.org_as,
                },
            )

            async with engine.begin() as conn:
                await conn.execute(stmt)
        except Exception as exc:
            LOG.exception(
                'Failed to save record to the database, error: %s, record: %s',
                exc,  # noqa: TRY401
                values,
            )
        else:
            self._already_added.add(ip)

    async def stop(self) -> None:
        """Бережно остановить плагин."""
        LOG.info('Nginx -> PostgreSQL geolocation plugin stopped')
