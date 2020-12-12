import logging
import time

import requests
from requests.auth import HTTPBasicAuth

LOGGER = logging.getLogger(__name__)


class InfluxDBPublisher(object):

    DEFAULT_INFLUX_PRECISION = "s"

    def __init__(
        self,
        host,
        database,
        port=8086,
        user=None,
        password=None,
        tags=None,
        precision=DEFAULT_INFLUX_PRECISION
    ):
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password

        self._auth = None
        if self._user and self._password:
            self._auth = HTTPBasicAuth(self._user, self._password)

        self._tags = tags or ""
        self._precision = precision

    @property
    def write_url(self):
        if not self._host or not self._port or not self._database:
            return None

        return (
            f"http://{self._host}:{self._port}/"
            f"write?db={self._database}&precision={self._precision}"
        )

    def publish(
        self,
        measurement,
        field_name,
        value,
        timestamp=None,
        tags=None
    ):
        if not self.write_url or not field_name:
            LOGGER.warning(
                "Cannot publish results to InfluxDB - "
                "credentials not available"
            )
            return

        if value == 0:
            LOGGER.warning(
                "Cannot publish results to InfluxDB - value = 0"
            )
            return

        timestamp = int(timestamp or time.time())
        tags = self._prepare_tags(tags)
        payload = f"{measurement},{tags} {field_name}={value} {int(timestamp)}"

        LOGGER.debug(
            f"Publishing value {value} into InfluxDB - as "
            f"'{measurement}.{field_name}'"
        )
        LOGGER.debug(f"InfluxDB query payload: '{payload}'")

        response = requests.post(
            self.write_url, payload.encode(),
            auth=self._auth
        )

        if response.ok:
            LOGGER.debug(
                "Influx DB publication succeeded for "
                f"{measurement}.{field_name}={value}"
            )
        else:
            LOGGER.error(
                "Influx DB publication failed for "
                f"{measurement}.{field_name}={value}"
            )

    def _prepare_tags(self, additional_tags=None):
        additional_tags = additional_tags or {}
        additional_tags_str = ",".join(
            f"{tag_name}={tag_value}"
            for tag_name, tag_value in additional_tags.items()
        )

        return f"{self._tags},{additional_tags_str}".strip(",")
