import json
import logging
import sys

import yaml

from influx import InfluxDBPublisher
from morizon import Morizon

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


def parse_config_yaml(path):
    with open(path) as file:
        return yaml.load(file, Loader=yaml.FullLoader)


if __name__ == "__main__":
    configuration = parse_config_yaml("config.yaml")
    LOGGER.info(
        "Morizon analyzer configuration: \n"
        f"{json.dumps(configuration, indent=2)}\n"
    )

    influx_publisher = (
        InfluxDBPublisher(**configuration["influx"])
        if "influx" in configuration
        else None
    )

    queries = [Morizon(**item) for item in configuration["queries"]]
    results = list(map(lambda query: query.read(), queries))

    LOGGER.info("RESULTS:")
    for result in results:
        LOGGER.info(result.dump())

        if not influx_publisher:
            LOGGER.warning(
                "No instance of InfluxDB available - "
                "results publication will be skipped"
            )
            continue

        influx_publisher.publish(**result.influxdb_measurement_average_price)
        influx_publisher.publish(
            **result.influxdb_measurement_average_price_per_squared_meter
        )
        influx_publisher.publish(**result.influxdb_measurement_offers_amount)
