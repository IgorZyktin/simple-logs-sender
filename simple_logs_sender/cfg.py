"""Простой класс конфига, который извлекает настройки из переменных окружения."""

from dataclasses import dataclass
from dataclasses import field
from typing import Annotated

import python_utilz as pu
import ujson


@dataclass
class Config(pu.BaseConfig):
    """Конфигурация приложения.

    Пример оформления настройки плагинов: {"tag1": ["plugin1", "plugin2"]}
    """

    host: str = '127.0.0.1'
    port: int = 5999
    log_file: str = ''
    log_format: str = '%(asctime)s - %(levelname)s - %(message)s'
    verbose: bool = True

    plugins_path: str = './plugins'
    plugins: Annotated[dict[str, list[str]], ujson.loads] = field(default_factory=dict)
