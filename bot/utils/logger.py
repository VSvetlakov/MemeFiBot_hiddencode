import sys
from loguru import logger

fmt = " | ".join((
    "<white>{time:YYYY-MM-DD HH:mm:ss}</white>",
    "<level>{level}</level>",
    "{extra[name]}",
    "<white><b>{message}</b></white>"
))

logger.remove()
logger.add(sink=sys.stdout, level="INFO", format=fmt)
logger = logger.opt(colors=True).bind(name="Default Logger")