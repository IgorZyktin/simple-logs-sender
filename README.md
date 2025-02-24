# simple-logs-sender

Сервер для пересылки логов из `rsyslog`.

## Зачем

Если хотите самостоятельно перекладывать логи, по дороге парсить их или как-то модифицировать.

## Установка и запуск

### Создание пользователя

Отдельный пользователь не обязателен, но лучше всё-же ограничить приложение.

```shell
sudo adduser simple_logs_sender
sudo mkdir /etc/simple_logs_sender
sudo chown simple_logs_sender /etc/simple_logs_sender
sudo su - simple_logs_sender
```

### Получение кода

```shell
git clone https://github.com/IgorZyktin/simple-logs-sender.git && cd simple-logs-sender
python3 -m venv .venv
source .venv/bin/activate
pip3 install .
```

### Тестовый запуск

Находясь там же, в каталоге `simple-logs-sender`.

```shell
export SLS_PLUGINS='{"test":"dummy"}'
python3 -m simple_logs_sender
```

Пример лога успешного запуска:

```
2025-02-24 17:01:00,096 - INFO - Simple logs sender starting
2025-02-24 17:01:00,097 - INFO - TCP server started on 127.0.0.1:5999
```

### Полноценный запуск - настройка источника данных

В качестве источника данных возьмём `NGINX`.

```shell
sudo vim /etc/nginx/nginx.conf
```

Добавим вывод логов в `JSON` формате.

```
http {
    ...
    log_format json_output '{'
        '"path": "$request_uri", '
        '"ip": "$remote_addr", '
        '"time": "$time_iso8601", '
        '"user_agent": "$http_user_agent", '
        '"user_id_got": "$uid_got", '
        '"user_id_set": "$uid_set", '
        '"remote_user": "$remote_user", '
        '"request": "$request", '
        '"status": "$status", '
        '"body_bytes_sent": "$body_bytes_sent", '
        '"request_time": "$request_time", '
        '"http_referrer": "$http_referer"}';
    access_log /var/log/nginx/access.log;
    access_log /var/log/nginx/access_json.log json_output;
    ...
}
```

```shell
sudo nginx -t
sudo systemctl restart nginx
```

### Полноценный запуск - настройка получателя данных

Создадим файл настройки для `rsyslog`.

```shell
sudo vim /etc/rsyslog.d/100-simple-logs-sender.conf
```

```
module(load="imfile")
input(type="imfile"
      File="/var/log/nginx/access_json.log"
      Tag="sls-nginx")

template(name="json_syslog" type="list") {
    constant(value="{")
    constant(value="\"timestamp\":\"")    property(name="timereported" dateFormat="rfc3339")
    constant(value="\",\"tag\":\"")       property(name="syslogtag" format="json")
    constant(value="\",\"hostname\":\"")  property(name="hostname" caseconversion="lower")
    constant(value="\",\"message\":\"")   property(name="rawmsg" format="json")
    constant(value="\"}\n")
}

if($syslogtag startswith 'sls-') then {
  action(
    type="omfwd" 
    target="127.0.0.1" 
    port="5999" 
    protocol="tcp"
    action.resumeRetryCount="100" 
    template="json_syslog"
    queue.type="linkedList" 
    queue.size="10000"
  )
}
```

```shell
sudo systemctl restart rsyslog
```

Или:

```shell
sudo service rsyslog restart
```

### Полноценный запуск - настройка сервиса

```shell
sudo vim /etc/simple_logs_sender/env
```

Содержимое настроек:

```
SLS_PLUGINS={"sls-nginx": ["dummy"]}
```

```shell
sudo chown simple_logs_sender env
sudo vim /etc/systemd/system/slsd.service
```

```
[Unit]
Description=Simple server that receives logs from rsyslog and sends them to other applications
After=syslog.target network.target
Wants=network.target

[Service]
User=simple_logs_sender
WorkingDirectory=/home/simple_logs_sender/simple-logs-sender/
ExecStart=/home/simple_logs_sender/simple-logs-sender/.venv/bin/python3 -m simple_logs_sender
EnvironmentFile=/etc/simple_logs_sender/env
CPUAccounting=true
MemoryAccounting=true
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```shell
sudo systemctl daemon-reload
sudo systemctl start slsd
sudo systemctl status slsd
sudo systemctl enable slsd
```

### Проверка работы

```shell
sudo journalctl -xu slsd -f
```

#### Ещё пример настройки пересылки логов

* https://www.shubhamdipt.com/blog/send-nginx-logs-to-sql-database/
