import os
import logging
from logging.handlers import RotatingFileHandler


PATH_DIR = 'loggs'

if not os.path.exists(PATH_DIR):
    os.mkdir(PATH_DIR)

# Создание логера
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Создание хэндлеров
file_log = RotatingFileHandler(f'{PATH_DIR}/logs.txt', maxBytes=5242880,
    backupCount=20, encoding='utf-8')
console_log = logging.StreamHandler()

# Создание формата сообщений
fmt = '\n[%(levelname)s]\nMODULE: %(pathname)s\nLINE: %(' \
      'lineno)s\nTIME: %(asctime)s\nMESSAGE: %(message)s'
datefmt = '%d.%m.%Y %H:%M:%S'
formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

# Установка формата сообщений
file_log.setFormatter(formatter)
console_log.setFormatter(formatter)

# Добавление хэндлеров к логеру
logger.addHandler(file_log)
logger.addHandler(console_log)