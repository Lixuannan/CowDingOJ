import logging
import os


def get_logger(name=__name__, log_level=None, log_file=None):
    """
    Get a unified Logger object.
    获取一个统一格式的 Logger 对象。

    Args 参数:
      - name: Logger 的名称，通常使用模块的 __name__。
      - level: 日志级别（例如 "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"），默认为 INFO。

    Retern 返回:
      - A configged logger  
        配置好的 Logger 对象，带有控制台和（可选）文件处理器，日志格式统一。
    """
    # 如果未指定日志级别，则从环境变量中读取，默认 INFO
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if not logger.handlers:
        # 设置日志级别
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # 定义统一格式
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 添加控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 如果环境变量中配置了日志文件路径，则添加文件处理器
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger
