"""
Пример использования S3-клиента с логами.
Перед запуском: скопируйте .env.example в .env и заполните ключи.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from s3_client import setup_logging, S3Client, get_logger

load_dotenv()


def main():
    # Логи в консоль и в файл logs/s3_client.log (для отладки: level=logging.DEBUG)
    setup_logging(level=logging.INFO)
    log = get_logger()

    bucket = os.getenv("S3_BUCKET") or os.getenv("AWS_BUCKET")
    if not bucket:
        log.error("Укажите S3_BUCKET или AWS_BUCKET в .env")
        return

    client = S3Client(bucket=bucket)

    # 1) Список объектов (например, с префиксом "uploads/")
    log.info("--- Список объектов ---")
    try:
        objects = client.list_objects(prefix="", max_keys=20)
        for obj in objects:
            log.info("  %s | %s bytes | %s", obj["Key"], obj["Size"], obj["LastModified"])
    except Exception as e:
        log.exception("Ошибка при получении списка: %s", e)
        return

    # 2) Скачать один файл (раскомментируйте и укажите свой key)
    # key = "path/to/file.pdf"
    # client.download_file(key, local_dir=Path("./downloads"))

    # 3) Скачать в память (bytes)
    # data = client.download_file_to_buffer(key)

    # 4) Presigned URL для отдачи ссылки на скачивание
    # url = client.get_presigned_url(key, expiration=3600)
    # log.info("Ссылка: %s", url)

    log.info("Готово.")


if __name__ == "__main__":
    main()
