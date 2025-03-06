# main.py
from kafka import KafkaConsumer

import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import common
import common.logger

db = common.db.get_database()
system_config = common.db.get_system_config()
consumer = KafkaConsumer(
    "submission-queue",
    bootstrap_servers=["localhost:9092"],
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="my-group",
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
)
logger = common.logger.get_logger(name=__name__, log_level=system_config["log_level"])
