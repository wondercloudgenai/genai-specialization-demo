import logging
import os
from settings import setting
from tools.logger_util import LoggerTool
from tools.path_util import PathUtil
from tools.redis_cache_template import RedisCacheTemplate


logger = LoggerTool.create_logger(
    logger_filepath=os.path.join(PathUtil.log_path, "app_run_log"),
    logger_info_console=logging.DEBUG,
    logger_info_file=logging.INFO,
    logger_level=logging.DEBUG
)
cache_template = RedisCacheTemplate(redis_url=setting.REDIS_URL)
