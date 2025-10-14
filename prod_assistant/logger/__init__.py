from .custom_logger import CustomLogger

# Create a single global structured logger instance for the app
GLOBAL_LOGGER = CustomLogger().get_logger(__name__)


