# Плагин для пересылки логов в PostgreSQL

## Создание пользователя

```shell
sudo -u postgres psql postgres
```

```sql
CREATE ROLE logger LOGIN PASSWORD 'qwerty';
CREATE DATABASE logs WITH OWNER = logger;
```

## Изменение конфигурации

```shell
sudo vim /etc/simple_logs_sender/env
```

Добавить URL базы данных:

```
SLS__POSTGRESQL__DB_URL='postgresql://logger:qwerty@192.168.1.2:5432/logs'
```
