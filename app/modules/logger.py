import logging
from logging.handlers import RotatingFileHandler

file_handler = RotatingFileHandler(
    "app.log", maxBytes=10000000, backupCount=1, encoding="utf8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
