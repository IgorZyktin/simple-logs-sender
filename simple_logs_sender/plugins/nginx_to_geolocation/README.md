# Плагин для определения координат запроса и пересылки в PostgreSQL

## Работа

При получении нового IP адреса делает запрос к https://ip-api.com/

Пример запроса:

```shell
curl http://ip-api.com/json/24.48.0.1
```

Пример ответа:

```json
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
```

## Создание пользователя

```shell
sudo -u postgres psql postgres
```

Если нет пользователя:

```sql
CREATE ROLE logger LOGIN PASSWORD 'qwerty';
CREATE DATABASE logs WITH OWNER = logger;
```

Создание таблицы:

```sql
CREATE TABLE ip_geolocation (
    ip varchar(15) primary key not null,
    updated_at timestamp with time zone not null,
    country varchar(255),
    country_code varchar(255),
    region varchar(255),
    region_name varchar(255),
    city varchar(255),
    zip varchar(255),
    lat float,
    lon float,
    ip_timezone varchar(255),
    isp varchar(255),
    org varchar(255),
    org_as varchar(255)
);
```

## Изменение конфигурации

```shell
sudo vim /etc/simple_logs_sender/env
```

Добавить URL базы данных (если нет в других плагинах):

```
SLS__POSTGRESQL__DB_URL='postgresql://logger:qwerty@192.168.1.2:5432/logs'
```
