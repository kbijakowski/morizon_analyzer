import logging

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)


class Result:
    def __init__(
        self,
        city,
        district,
        offer_type,
        filters,
        average_price,
        average_price_per_squared_meter,
        offers_amount,
    ):
        self.city = city
        self.district = district
        self.offer_type = offer_type
        self.filters = filters

        self.average_price = average_price
        self.average_price_per_squared_meter = average_price_per_squared_meter
        self.offers_amount = offers_amount

    def dump(self):
        district = f" [{self.district}]" if self.district else ""
        return f"{self.offer_type} {self.city}{district}: {self.average_price} zł ({self.average_price_per_squared_meter} zł/m2) [{self.offers_amount}]"  # noqa: E501

    @property
    def influxdb_tags(self):
        result = {
            "city": self.city,
            "district": self.district or "null"
        }

        for filter_name, filter_value in self.filters.items():
            result[filter_name] = filter_value if filter_value else "null"

        return result

    @property
    def influxdb_measurement_average_price(self):
        return {
            "measurement": self.offer_type,
            "field_name": "average_price",
            "value": self.average_price,
            "tags": self.influxdb_tags,
        }

    @property
    def influxdb_measurement_average_price_per_squared_meter(self):
        return {
            "measurement": self.offer_type,
            "field_name": "average_price_per_squared_meter",
            "value": self.average_price_per_squared_meter,
            "tags": self.influxdb_tags,
        }

    @property
    def influxdb_measurement_offers_amount(self):
        return {
            "measurement": self.offer_type,
            "field_name": "offers_amount",
            "value": self.offers_amount,
            "tags": self.influxdb_tags,
        }


class Morizon:

    TEXT_AVERAGE_PRICE = "średnia cena"
    TEXT_LISTING_HEADER_DESCRIPTION_BEGINING = "Znaleziono"
    TEXT_LISTING_HEADER_DESCRIPTION_END = "ogłosz"
    DEFAULT_MAIN_URL = "https://www.morizon.pl"
    DEFAULT_OFFER_TYPE = "mieszkania"

    @staticmethod
    def _to_int(value):
        try:
            return int(
                "".join(
                    [character for character in value if character.isdigit()]
                )
            )
        except ValueError:
            return 0

    def __init__(
        self,
        city,
        district=None,
        main_url=DEFAULT_MAIN_URL,
        offer_type=DEFAULT_OFFER_TYPE,
        filter_living_area_from=None,
        filter_number_of_rooms_from=None,
        filter_floor_from=None,
        filter_price_from=None,
        filter_dict_building_type=None,
        filter_date_filter=None,
        filter_with_price=None,
    ):
        """
        :param `filter_living_area_from`: space in squared meters
        (lower boundary)
        :param `filter_number_of_rooms_from`:  number of rooms (lower boundary)
        :param `filter_floor_from`: floor (lower boundary)
        :param `filter_price_from`: total price in zł (lower boundary)
        :param `filter_dict_building_type`: building type (247 - `kamienica`)
        :param `filter_date_filter`: number of days from offer publication
        (allowed values: 1, 3, 7, 30, 90, 180)
        :param `filter_with_price`: only offers with price (value: 1)
        """
        self.city = city
        self.district = district
        self.main_url = main_url
        self.offer_type = offer_type

        self.all_filters = {
            "price_from": filter_price_from,
            "living_area_from": filter_living_area_from,
            "number_of_rooms_from": filter_number_of_rooms_from,
            "floor_from": filter_floor_from,
            "dict_building_type": filter_dict_building_type,
            "date_filter": filter_date_filter,
            "with_price": filter_with_price,
        }
        self.filters = {
            filter_name: filter_value
            for filter_name, filter_value in self.all_filters.items()
            if filter_value
        }

    @property
    def url(self):
        district = f"/{self.district}" if self.district else ""
        filters_rendered = "&".join(
            [
                f"ps%5B{filter_name}%5D={filter_value}"
                for filter_name, filter_value in self.filters.items()
                if filter_value
            ]
        )

        return f"{self.main_url}/{self.offer_type}/{self.city}{district}/?{filters_rendered}"  # noqa: E501

    def read(self):
        markup = BeautifulSoup(self._get_webpage_content(), "html.parser")

        links = markup.find_all("a", {"id": "locationPageLink"})
        average_price, average_price_per_squared_meter = self._parse_links(
            links
        )

        listing_header_description = markup.find_all(
            "p", {"class": "listing-header__description"}
        )
        offers_amount = self._parse_listing_header_description(
            listing_header_description
        )

        return Result(
            self.city,
            self.district,
            self.offer_type,
            self.all_filters,
            average_price,
            average_price_per_squared_meter,
            offers_amount,
        )

    def _get_webpage_content(self):
        LOGGER.debug(f"GET {self.url}")
        response = requests.get(self.url)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            LOGGER.warning(
                "Request for {0} failed. Error: {1}".format(self.url, e)
            )
            return None

        return response.content

    def _parse_links(self, links):
        if len(links) == 0:
            return (0, 0)

        for link in links:
            text = link.text
            assert text.startswith(self.TEXT_AVERAGE_PRICE)
            text = text.split(self.TEXT_AVERAGE_PRICE)[-1]

            average_price = self._to_int(text.split("zł")[0])
            average_price_per_squared_meter = self._to_int(
                text.split("(")[1].split("zł")[0]
            )

            return average_price, average_price_per_squared_meter

    def _parse_listing_header_description(self, listing_header_description):
        assert listing_header_description
        listing_header_description_p_tag = listing_header_description.pop()

        result = listing_header_description_p_tag.text.split(
            self.TEXT_LISTING_HEADER_DESCRIPTION_BEGINING
        )[-1].split(self.TEXT_LISTING_HEADER_DESCRIPTION_END)[0]

        return self._to_int(result)
