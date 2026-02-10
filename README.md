# Receiving data from S3 on Python

Удобный Python-клиент для работы с **S3-совместимым хранилищем**: получение файлов, список объектов, логирование операций. Подходит для AWS S3, Yandex Object Storage и других S3-совместимых сервисов.

---

## Что это за приложение

Это библиотека и набор скриптов для:

- **получения файлов** из S3 (скачивание в файл или в память);
- **просмотра списка объектов** в бакете (с префиксом и пагинацией);
- **генерации presigned URL** для временного доступа к файлам;
- **получения метаданных** объекта (размер, тип, дата изменения);
- **логирования** всех операций в консоль и в файл с ротацией.

Логи помогают отлаживать запросы и отслеживать ошибки в продакшене.

---

## Возможности

| Возможность | Описание |
|-------------|----------|
| Скачивание в файл | `download_file(key, local_path)` — сохранение объекта в указанный путь или папку |
| Скачивание в память | `download_file_to_buffer(key)` — возвращает `bytes` |
| Список объектов | `list_objects(prefix, max_keys)` — список ключей с размером и датой (с пагинацией) |
| Presigned URL | `get_presigned_url(key, expiration)` — временная ссылка для скачивания |
| Метаданные | `get_object_metadata(key)` — размер, Content-Type, LastModified |
| Логирование | Файл `logs/s3_client.log` + консоль, ротация по размеру (5 MB, 3 бэкапа) |
| Конфигурация | Ключи и бакет через `.env` или параметры конструктора |

---

## Требования

- Python 3.10+
- Доступ к S3-совместимому хранилищу (ключи доступа и имя бакета)

---

## Установка

```bash
# Клонирование репозитория
git clone https://github.com/GoreWorste/receiving-data-from-S3-on-Python.git
cd receiving-data-from-S3-on-Python

# Виртуальное окружение (рекомендуется)
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux / macOS

# Зависимости
pip install -r requirements.txt
```

---

## Настройка

1. Скопируйте шаблон переменных окружения:

   ```bash
   copy env.example .env   # Windows
   # cp env.example .env  # Linux / macOS
   ```

2. Откройте `.env` и укажите свои данные:

   ```env
   AWS_ACCESS_KEY_ID=ваш_ключ
   AWS_SECRET_ACCESS_KEY=ваш_секретный_ключ
   AWS_REGION=ru-central1
   S3_BUCKET=имя_бакета
   ```

   Для **Yandex Object Storage** добавьте:

   ```env
   AWS_ENDPOINT_URL=https://storage.yandexcloud.net
   ```

   Для **AWS S3** достаточно региона и ключей (endpoint указывать не нужно).

---

## Использование

### Быстрый старт

```python
import logging
import os
from s3_client import S3Client, setup_logging, get_logger

# Включить логи в консоль и в файл logs/s3_client.log
setup_logging(level=logging.INFO)
log = get_logger()

client = S3Client(bucket=os.getenv("S3_BUCKET"))

# Список объектов
objects = client.list_objects(prefix="uploads/", max_keys=50)
for obj in objects:
    print(obj["Key"], obj["Size"], obj["LastModified"])

# Скачать файл в папку
client.download_file("documents/report.pdf", local_dir="./downloads")

# Скачать в память
data = client.download_file_to_buffer("documents/report.pdf")

# Временная ссылка на скачивание (1 час)
url = client.get_presigned_url("documents/report.pdf", expiration=3600)
print(url)
```

### Запуск примера из репозитория

```bash
python example_usage.py
```

Скрипт выведет список объектов в бакете (если они есть) и запишет те же события в `logs/s3_client.log`.

### Настройка логгера

```python
import logging
from s3_client import setup_logging

# Только консоль, уровень DEBUG
setup_logging(level=logging.DEBUG, log_to_file=False)

# Файл + консоль, свои лимиты ротации
setup_logging(
    level=logging.INFO,
    max_bytes=10 * 1024 * 1024,  # 10 MB
    backup_count=5,
)
```

---

## Структура проекта

```
receiving-data-from-S3-on-Python/
├── s3_client.py      # Основной модуль: S3Client и настройка логов
├── example_usage.py  # Пример использования
├── requirements.txt  # boto3, python-dotenv
├── env.example       # Шаблон для .env
├── logs/             # Директория логов (создаётся автоматически)
│   └── s3_client.log
└── README.md
```

---

## Совместимость

- **AWS S3**
- **Yandex Object Storage** (через `AWS_ENDPOINT_URL=https://storage.yandexcloud.net`)
- Любое другое S3-совместимое API (MinIO, DigitalOcean Spaces и т.д.) — укажите свой `endpoint_url`.

---

## Лицензия

Свободное использование в своих проектах.

с ❤️ от GoreWorste
