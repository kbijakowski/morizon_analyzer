import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)


class AnalyticsResult:

    def __init__(
        self,
        city: str,
        district: str,
        offer_type: str,
        filters: Dict[str, Any],
        average_price: float,
        average_price_per_squared_meter: float,
        offers_amount: int,
    ):
        self.city = city
        self.district = district
        self.offer_type = offer_type
        self.filters = filters

        self.average_price = average_price
        self.average_price_per_squared_meter = average_price_per_squared_meter
        self.offers_amount = offers_amount

    def dump(self) -> str:
        district = f" [{self.district}]" if self.district else ""
        return f"{self.offer_type} {self.city}{district}: {self.average_price} zł ({self.average_price_per_squared_meter} zł/m2) [{self.offers_amount}]"  # noqa: E501

    @property
    def influxdb_tags(self) -> Dict[str, Union[str, int]]:
        result = {
            "city": self.city,
            "district": self.district or "null"
        }

        for filter_name, filter_value in self.filters.items():
            result[filter_name] = filter_value if filter_value else "null"

        return result

    @property
    def influxdb_measurement_average_price(self) -> Optional[Dict[str, Any]]:
        if not self.average_price:
            return None

        return {
            "measurement": self.offer_type,
            "field_name": "average_price",
            "value": self.average_price,
            "tags": self.influxdb_tags,
        }

    @property
    def influxdb_measurement_average_price_per_squared_meter(
        self
    ) -> Optional[Dict[str, Any]]:
        if not self.average_price_per_squared_meter:
            return None

        return {
            "measurement": self.offer_type,
            "field_name": "average_price_per_squared_meter",
            "value": self.average_price_per_squared_meter,
            "tags": self.influxdb_tags,
        }

    @property
    def influxdb_measurement_offers_amount(self) -> Optional[Dict[str, Any]]:
        if not self.offers_amount:
            return None

        return {
            "measurement": self.offer_type,
            "field_name": "offers_amount",
            "value": self.offers_amount,
            "tags": self.influxdb_tags,
        }


class ReportingResult:

    def __init__(self, url: str, title: str, price: str):
        self.url = url
        self.title = title.strip().replace("\xa0", "").replace("\xa0", "")
        self.price = price

    def dump(self) -> str:
        return f"{self.title} ({self.price} zł)\n{self.url}"  # noqa: E501

    def to_html(self, number_in_order: Optional[int] = None) -> str:
        number_in_order_str = f"{str(number_in_order)}. " or ""

        return f"""
        <h4>{number_in_order_str}{self.title}</h4>
        <p>{self.price} zł</p>
        <a href="{self.url}">{self.url}</a>
        <br/><br/>
        """


class Query:

    TEXT_AVERAGE_PRICE = "średnia cena"
    TEXT_LISTING_HEADER_DESCRIPTION_BEGINING = "Znaleziono"
    TEXT_LISTING_HEADER_DESCRIPTION_END = "ogłosz"
    DEFAULT_MAIN_URL = "https://www.morizon.pl"
    DEFAULT_OFFER_TYPE = "mieszkania"

    @staticmethod
    def _to_int(value: str) -> int:
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
        city: str,
        district: Optional[str] = None,
        main_url: Optional[str] = DEFAULT_MAIN_URL,
        offer_type: Optional[str] = DEFAULT_OFFER_TYPE,
        filter_living_area_from: Optional[float] = None,
        filter_number_of_rooms_from: Optional[int] = None,
        filter_floor_from: Optional[int] = None,
        filter_price_from: Optional[float] = None,
        filter_price_to: Optional[float] = None,
        filter_dict_building_type: Optional[int] = None,
        filter_date_filter: Optional[int] = None,
        filter_with_price: Optional[int] = None,
    ):
        """
        :param `filter_living_area_from`: space in squared meters
        (lower boundary)
        :param `filter_number_of_rooms_from`:  number of rooms (lower boundary)
        :param `filter_floor_from`: floor (lower boundary)
        :param `filter_price_from`: total price in zł (lower boundary)
        :param `filter_price_to`: total price in zł (higher boundary)
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
            "price_to": filter_price_to,
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
    def url(self) -> str:
        district = f"/{self.district}" if self.district else ""
        filters_rendered = "&".join(
            [
                f"ps%5B{filter_name}%5D={filter_value}"
                for filter_name, filter_value in self.filters.items()
                if filter_value
            ]
        )

        return f"{self.main_url}/{self.offer_type}/{self.city}{district}/?{filters_rendered}"  # noqa: E501

    def to_html(self) -> str:
        filters_dump = "".join(
            [
                f"<li>{filter_name}: {filter_value}</li>\n"
                for filter_name, filter_value in self.all_filters.items()
                if filter_value
            ]
        )

        return f"""
        <h2>{self.city} {self.district}</h2>
        <ul>
        <li>{self.offer_type}</li>
        {filters_dump}
        </ul>
        """

    def read_for_analytics(self) -> AnalyticsResult:
        markup = BeautifulSoup(self._get_webpage_content(), "html.parser")

        links = markup.find_all("a", {"id": "locationPageLink"})
        average_price, average_price_per_squared_meter = self._parse_location_page_links(  # noqa: E501
            links
        )

        listing_header_description = markup.find_all(
            "p", {"class": "listing-header__description"}
        )
        offers_amount = self._parse_listing_header_description(
            listing_header_description
        )

        return AnalyticsResult(
            self.city,
            self.district,
            self.offer_type,
            self.all_filters,
            average_price,
            average_price_per_squared_meter,
            offers_amount,
        )

    def read_for_reporting(self) -> List[ReportingResult]:
        markup = BeautifulSoup(self._get_webpage_content(), "html.parser")
        links = markup.find_all("a", {"class": "property-url"})

        return self._parse_property_url_links(links)

    def _get_webpage_content(self) -> Optional[str]:
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

    def _parse_property_url_links(self, links: List) -> List[ReportingResult]:
        result = []

        for link in links:
            result.append(
                ReportingResult(
                    url=link["href"],
                    title=link.find("h2", {"class": "single-result__title"}).get_text(),  # noqa: E501
                    price=link.find("meta", {"itemprop": "price"})["content"],
                )
            )

        return result

    def _parse_location_page_links(self, links: List[str]) -> Tuple[int, int]:
        if len(links) == 0:
            return (None, None)

        for link in links:
            text = link.text
            assert text.startswith(self.TEXT_AVERAGE_PRICE)
            text = text.split(self.TEXT_AVERAGE_PRICE)[-1]

            average_price = self._to_int(text.split("zł")[0])
            average_price_per_squared_meter = self._to_int(
                text.split("(")[1].split("zł")[0]
            )

            return average_price, average_price_per_squared_meter

    def _parse_listing_header_description(
        self,
        listing_header_description: str
    ) -> int:
        if not listing_header_description:
            return 0

        listing_header_description_p_tag = listing_header_description.pop()

        result = listing_header_description_p_tag.text.split(
            self.TEXT_LISTING_HEADER_DESCRIPTION_BEGINING
        )[-1].split(self.TEXT_LISTING_HEADER_DESCRIPTION_END)[0]

        return self._to_int(result)
