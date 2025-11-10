# -*- coding: utf-8 -*-
"""
@author:  bingo(bingyl123@163.com)
@versions: 1.0.0
@file:    logger_tool.py
@time:    2023/1/13 18:02
"""
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler


class LoggerTool:
    """
    %(name)s            Name of the logger (logging channel)
    %(levelno)s         Numeric logging level for the message (DEBUG, INFO,
                        WARNING, ERROR, CRITICAL)
    %(levelname)s       Text logging level for the message ("DEBUG", "INFO",
                        "WARNING", "ERROR", "CRITICAL")
    %(pathname)s        Full pathname of the source file where the logging
                        call was issued (if available)
    %(filename)s        Filename portion of pathname
    %(module)s          Module (name portion of filename)
    %(lineno)d          Source line number where the logging call was issued
                        (if available)
    %(funcName)s        Function name
    %(created)f         Time when the LogRecord was created (time.time()
                        return value)
    %(asctime)s         Textual time when the LogRecord was created
    %(msecs)d           Millisecond portion of the creation time
    %(relativeCreated)d Time in milliseconds when the LogRecord was created,
                        relative to the time the logging module was loaded
                        (typically at application startup time)
    %(thread)d          Thread ID (if available)
    %(threadName)s      Thread name (if available)
    %(process)d         Process ID (if available)
    %(message)s         The result of record.getMessage(), computed just as
                        the record is emitted
    """

    @staticmethod
    def create_logger(**kwargs):
        logger_name = kwargs.get("logger_name", "root")
        logger_level = kwargs.get("logger_level", logging.INFO)
        logger_level_console = kwargs.get("logger_info_console", logging.INFO)
        logger_level_file = kwargs.get("logger_info_file", logging.DEBUG)
        formatter = kwargs.get("formatter", "%(asctime)s[%(levelname)s] %(pathname)s: %(message)s")
        date_formatter = kwargs.get("date_formatter", "%Y-%m-%d %H:%M:%S")
        logger_filepath = kwargs.get("logger_filepath")
        console_flag = kwargs.get("console_flag", True)
        filelog_flag = kwargs.get("filelog_flag", True)

        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)
        formatter = logging.Formatter(
            fmt=formatter,
            datefmt=date_formatter,
        )
        if console_flag:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logger_level_console)
            logger.addHandler(console_handler)
            logger.setLevel(logger_level)

        if filelog_flag and logger_filepath:
            file_handler = ConcurrentRotatingFileHandler(
                filename=logger_filepath,
                encoding="utf8",
                maxBytes=10 * 1024 * 1024,
                backupCount=100)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logger_level_file)
            logger.addHandler(file_handler)
        return logger
