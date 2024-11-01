import sys
from loguru import logger

logger.remove()
logger.add(
    level="DEBUG",
    sink=sys.stdout, 
    format="<white>{time:YYYY-MM-DD HH:mm:ss}</white>"
                                   " | <level>{level: <8}</level>"
                                   " | <cyan><b>{line}</b></cyan>"
                                   " - <white><b>{message}</b></white>")
logger.add("memefidev.log", level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", rotation="20 MB")

logger = logger.opt(colors=True)


class SessionLogger:

    session_name: str

    def __init__(self, session_name):
        self.session_name = session_name

    def trace(self, message):
        logger.trace(f"{self.session_name} | {message}")

    def debug(self, message):
        logger.debug(f"{self.session_name} | {message}")

    def info(self, message):
        logger.info(f"{self.session_name} | {message}")

    def success(self, message):
        logger.success(f"{self.session_name} | {message}")

    def warning(self, message):
        logger.warning(f"{self.session_name} | {message}")

    def error(self, message):
        logger.error(f"{self.session_name} | {message}")

    def critical(self, message):
        logger.critical(f"{self.session_name} | {message}")