import datetime
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import yaml

from influx import InfluxDBPublisher
from morizon import Query

formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)

root = logging.getLogger()
root.setLevel(logging.DEBUG)
root.addHandler(handler)


LOGGER = logging.getLogger(__name__)


DEFAULT_CONFIG_FILE_PATH = "config.yaml"
REPORTS_DIRECTORY = "reports"
ENV_VARIBLE_CONFIG_FILE_PATH = "MORIZON_ANALYZER_CONFIG_PATH"
ENV_VARIBLE_INFLUXDB_HOST = "INFLUXDB_HOST"
ENV_VARIBLE_INFLUXDB_PORT = "INFLUXDB_PORT"
ENV_VARIBLE_INFLUXDB_DB = "INFLUXDB_DB"
ENV_VARIBLE_INFLUXDB_USER = "INFLUXDB_USER"
ENV_VARIBLE_INFLUXDB_PASSWORD = "INFLUXDB_PASSWORD"


def get_config_file_path() -> str:
    return os.getenv(ENV_VARIBLE_CONFIG_FILE_PATH, DEFAULT_CONFIG_FILE_PATH)


def parse_config_yaml(path: str) -> Dict[str, Any]:
    with open(path) as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def get_influx_configuration(
    configuration: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    influx_confguration = configuration.get("influx", {})

    influx_host = os.getenv(ENV_VARIBLE_INFLUXDB_HOST)
    if influx_host:
        influx_confguration["host"] = influx_host

    influx_port = os.getenv(ENV_VARIBLE_INFLUXDB_PORT)
    if influx_port:
        influx_confguration["port"] = influx_port

    influx_database = os.getenv(ENV_VARIBLE_INFLUXDB_DB)
    if influx_database:
        influx_confguration["database"] = influx_database

    influx_user = os.getenv(ENV_VARIBLE_INFLUXDB_USER)
    if influx_user:
        influx_confguration["user"] = influx_user

    influx_password = os.getenv(ENV_VARIBLE_INFLUXDB_PASSWORD)
    if influx_password:
        influx_confguration["password"] = influx_password

    if not {"host", "database"}.issubset(influx_confguration.keys()):
        LOGGER.warning(
            "InfluxDB configuration is not complete - "
            "results will not be published"
        )
        return None

    return influx_confguration


def prepare_queries(
    configuration: Dict[str, Any],
    query_type: str
) -> List[Query]:
    return [
        Query(**item)
        for item in configuration.get("queries", {}).get(query_type, [])
    ]


def process_analytics_queries(
    queries: List[Query],
    influx_publisher: Optional[InfluxDBPublisher] = None
) -> None:
    results = list(map(lambda query: query.read_for_analytics(), queries))

    LOGGER.info("\n\nResults:")
    for result in results:
        LOGGER.info(result.dump())

    if not influx_publisher:
        LOGGER.warning(
            "No instance of InfluxDB available - "
            "results publication will be skipped"
        )
    else:
        LOGGER.info("\n\nPublishing results")
        for result in results:
            if result.influxdb_measurement_average_price:
                influx_publisher.publish(
                    **result.influxdb_measurement_average_price
                )

            if result.influxdb_measurement_average_price_per_squared_meter:
                influx_publisher.publish(
                    **result.influxdb_measurement_average_price_per_squared_meter  # noqa: E501
                )

            if result.influxdb_measurement_offers_amount:
                influx_publisher.publish(
                    **result.influxdb_measurement_offers_amount
                )


def process_reporting_queries(queries: List[Query]) -> None:
    timestamp = datetime.datetime.now()
    counter = 1
    reporting_results_html = "<h1>Report " \
        f"{timestamp.day:02d}.{timestamp.month:02d}.{timestamp.year} " \
        f"({timestamp.hour:02d}:{timestamp.minute:02d})</h1>" \

    for query in queries:
        reporting_results_html += query.to_html()
        reporting_results = query.read_for_reporting()

        for reporting_result in reporting_results:
            reporting_results_html += reporting_result.to_html(counter)
            counter += 1

        reporting_results_html += "<hr/>"

    write_report(timestamp, reporting_results_html)


def write_report(timestamp: datetime.datetime, content: str) -> None:
    file_name = f"{REPORTS_DIRECTORY}/report__{timestamp.year}_" \
        f"{timestamp.month:02d}_{timestamp.day:02d}__" \
        f"{timestamp.hour:02d}_{timestamp.minute:02d}.html" \

    with open(file_name, "w+") as _file:
        _file.write(content)


if __name__ == "__main__":
    config_file_path = get_config_file_path()
    LOGGER.info(
        "Morizon analyzer configuration file path: {config_file_path}"
    )

    configuration = parse_config_yaml(config_file_path)
    LOGGER.info(
        "Morizon analyzer configuration: \n"
        f"{json.dumps(configuration, indent=2)}\n"
    )

    influx_configuration = get_influx_configuration(configuration)
    influx_publisher = InfluxDBPublisher(**influx_configuration) \
        if influx_configuration \
        else None

    LOGGER.info("Processing analytics queries")
    analytics_queries = prepare_queries(configuration, "analytics")
    LOGGER.info(
        f"There are {len(analytics_queries)} analytics queries defined"
    )
    process_analytics_queries(analytics_queries, influx_publisher)

    LOGGER.info("Processing reporting queries ...")
    reporting_queries = prepare_queries(configuration, "reporting")
    LOGGER.info(
        f"There are {len(reporting_queries)} reporting queries defined"
    )
    process_reporting_queries(reporting_queries)
