import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Niveau de log par défaut : INFO
# Si APP_VERBOSE est "true", on peut passer en DEBUG si besoin,
# mais ici on va surtout l'utiliser pour filtrer les prints transformés en logs.
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
APP_VERBOSE = os.getenv("APP_VERBOSE", "false").lower() == "true"

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL_STR, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("IMT-Agent")

def log_info(message):
    """Log information if APP_VERBOSE is True or if it's important"""
    if APP_VERBOSE:
        logger.info(message)
    else:
        # En mode non-verbose, on peut choisir de ne rien logger ou
        # de ne logger que le strict minimum.
        # Pour l'instant, on reste discret.
        pass

def log_warn(message):
    logger.warning(message)

def log_error(message):
    logger.error(message)

def log_debug(message):
    logger.debug(message)

def log_important(message):
    """Toujours logger, même en mode non-verbose"""
    logger.info(message)
