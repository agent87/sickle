import os
from logging import getLogger, Formatter, StreamHandler, FileHandler, INFO, Logger


def create_logger(name, log_directory="logs") -> Logger:
    logger = getLogger(name)
    logger.setLevel(INFO)

    # Set the logging format
    formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create a StreamHandler
    stream_handler = StreamHandler()
    stream_handler.setFormatter(formatter)

    # Create a FileHandler
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    file_handler = FileHandler(os.path.join(log_directory, f"{name}.log"))
    file_handler.setFormatter(formatter)

    # Add both handlers to the logger
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger
