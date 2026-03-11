import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """
    Creates and returns a standardized logger instance.
    Format: [YYYY-MM-DD HH:MM:SS,ms] [LEVEL] [module.name]: Message
    """
    logger = logging.getLogger(name)
    
    # Only configure if it doesn't already have handlers to prevent double logging
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            fmt='[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Prevent propagation to the root logger to avoid duplicate prints
        logger.propagate = False

    return logger
