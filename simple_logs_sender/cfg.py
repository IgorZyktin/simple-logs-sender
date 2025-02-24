"""Простой класс конфига, который извлекает настройки из переменных окружения."""

from dataclasses import MISSING
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
import json
import os
import sys
from typing import Annotated
from typing import TypeVar
from typing import get_args
from typing import get_origin

import ujson


@dataclass
class BaseConfig:
    """Базовый класс сервера для наследования в плагинах."""


T_co = TypeVar('T_co', bound=BaseConfig, covariant=True)


def from_env(model_type: type[T_co], prefix: str = 'SLS__') -> T_co:
    """Собрать экземпляр из переменных окружения."""
    payload = {}
    for each_field in fields(model_type):
        if each_field.name.startswith('_'):
            continue

        env_name = f'{prefix}{each_field.name}'.upper()
        default = None if each_field.default is MISSING else each_field.default
        value = os.environ.get(env_name, default)

        if value is None:
            msg = f'You have to setup {env_name!r} environment variable'
            sys.exit(msg)

        if get_origin(each_field.type) is Annotated:
            expected_type, caster = get_args(each_field.type)[:2]
        else:
            expected_type = each_field.type
            caster = each_field.type

        try:
            casted = caster(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            msg = f'Failed to convert {env_name!r} to type {expected_type}, got {value!r}'
            sys.exit(msg)

        payload[each_field.name] = casted

    return model_type(**payload)


@dataclass
class Config(BaseConfig):
    """Конфигурация приложения.

    Пример оформления настройки плагинов: {"tag1": ["plugin1", "plugin2"]}
    """

    host: str = '127.0.0.1'
    port: int = 5999
    chunk_size: int = 2048
    log_file: str = ''
    log_format: str = '%(asctime)s - %(levelname)s - %(message)s'

    plugins_path: str = './plugins'
    plugins: Annotated[dict[str, list[str]], ujson.loads] = field(default_factory=dict)
