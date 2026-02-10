"""
Клиент для работы с AWS S3: получение файлов, список объектов, логирование.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# --- Настройка логирования ---

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "s3_client.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
) -> logging.Logger:
    """
    Настраивает логгер для S3-клиента.
    Логи пишутся в файл (с ротацией) и/или в консоль.
    """
    logger = logging.getLogger("s3_client")
    logger.setLevel(level)

    # Убираем старые хендлеры при повторном вызове
    logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    if log_to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


# Логгер по умолчанию (инициализируется при первом использовании)
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


# --- S3 клиент ---


class S3Client:
    """
    Обёртка над boto3 S3 с логированием операций и удобными методами.
    """

    def __init__(
        self,
        bucket: str,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.bucket = bucket
        self.log = logger or get_logger()

        region_name = region_name or os.getenv("AWS_REGION", "ru-central1")
        aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        endpoint_url = endpoint_url or os.getenv("AWS_ENDPOINT_URL")

        session_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self._session = boto3.Session(**session_kwargs)
        client_kwargs = {}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url

        self._client = self._session.client("s3", **client_kwargs)
        self.log.info("S3 клиент инициализирован: bucket=%s, region=%s", bucket, region_name)

    def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 1000,
        delimiter: Optional[str] = None,
    ) -> list[dict]:
        """
        Список объектов в бакете (с опциональным префиксом).
        Возвращает список словарей с ключами: Key, Size, LastModified, ETag.
        """
        self.log.debug("list_objects: prefix=%r, max_keys=%s", prefix, max_keys)
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            result = []
            for page in paginator.paginate(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
                Delimiter=delimiter or "",
            ):
                for obj in page.get("Contents", []):
                    result.append(
                        {
                            "Key": obj["Key"],
                            "Size": obj.get("Size", 0),
                            "LastModified": obj.get("LastModified"),
                            "ETag": obj.get("ETag"),
                        }
                    )
            self.log.info("list_objects: получено записей=%s (prefix=%r)", len(result), prefix)
            return result
        except ClientError as e:
            self.log.exception("list_objects ошибка: %s", e)
            raise

    def download_file(
        self,
        key: str,
        local_path: Optional[str | Path] = None,
        local_dir: Optional[str | Path] = None,
    ) -> Path:
        """
        Скачивает объект из S3 в локальный файл.
        local_path — полный путь к файлу; если не задан, используется local_dir + имя ключа.
        """
        local_path = Path(local_path) if local_path else None
        local_dir = Path(local_dir) if local_dir else Path(".")

        if local_path is None:
            local_path = local_dir / Path(key).name

        local_path.parent.mkdir(parents=True, exist_ok=True)
        self.log.info("download_file: key=%s -> %s", key, local_path)

        try:
            self._client.download_file(self.bucket, key, str(local_path))
            size = local_path.stat().st_size
            self.log.info("download_file: успешно, размер=%s bytes", size)
            return local_path
        except ClientError as e:
            self.log.exception("download_file ошибка: key=%s, error=%s", key, e)
            raise

    def download_file_to_buffer(self, key: str) -> bytes:
        """Скачивает объект в память и возвращает bytes."""
        self.log.debug("download_file_to_buffer: key=%s", key)
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            data = response["Body"].read()
            self.log.info("download_file_to_buffer: key=%s, размер=%s bytes", key, len(data))
            return data
        except ClientError as e:
            self.log.exception("download_file_to_buffer ошибка: key=%s, error=%s", key, e)
            raise

    def get_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "get_object",
    ) -> str:
        """Генерирует presigned URL для скачивания (по умолчанию на 1 час)."""
        self.log.debug("get_presigned_url: key=%s, expiration=%s", key, expiration)
        try:
            url = self._client.generate_presigned_url(
                method,
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiration,
            )
            self.log.info("get_presigned_url: сгенерирован для key=%s", key)
            return url
        except ClientError as e:
            self.log.exception("get_presigned_url ошибка: key=%s, error=%s", key, e)
            raise

    def get_object_metadata(self, key: str) -> dict:
        """Возвращает метаданные объекта (ContentLength, LastModified, ContentType и т.д.)."""
        self.log.debug("get_object_metadata: key=%s", key)
        try:
            response = self._client.head_object(Bucket=self.bucket, Key=key)
            meta = {
                "ContentLength": response.get("ContentLength"),
                "LastModified": response.get("LastModified"),
                "ContentType": response.get("ContentType"),
                "ETag": response.get("ETag"),
            }
            self.log.info("get_object_metadata: key=%s, size=%s", key, meta.get("ContentLength"))
            return meta
        except ClientError as e:
            self.log.exception("get_object_metadata ошибка: key=%s, error=%s", key, e)
            raise


# --- Точка входа для быстрого теста ---

if __name__ == "__main__":
    setup_logging(level=logging.DEBUG)
    log = get_logger()

    bucket = os.getenv("S3_BUCKET") or os.getenv("AWS_BUCKET")
    if not bucket:
        log.warning("Задайте S3_BUCKET или AWS_BUCKET в .env для теста")
    else:
        client = S3Client(bucket=bucket)
        try:
            objects = client.list_objects(prefix="", max_keys=10)
            log.info("Найдено объектов: %s", len(objects))
            for obj in objects[:5]:
                log.info("  %s (%s bytes)", obj["Key"], obj["Size"])
        except Exception as e:
            log.exception("Ошибка: %s", e)
