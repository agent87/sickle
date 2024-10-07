# coding: utf-8
"""
    sickle.response
    ~~~~~~~~~~~~~~~

    :copyright: Copyright 2015 Mathias Loesch
"""

from lxml import etree
from typing import Dict, Any
import requests

XMLParser = etree.XMLParser(remove_blank_text=True, recover=True, resolve_entities=False)


class OAIResponse(object):
    """A response from an OAI server.

    Provides access to the returned data on different abstraction
    levels.

    :param http_response: The original HTTP response.
    :param params: The OAI parameters for the request.
    :type params: dict
    """

    def __init__(self, http_response: requests.Response, params: Dict[str, Any]) -> None:
        self.params = params
        self.http_response = http_response

    @property
    def raw(self) -> str:
        """The server's response as unicode."""
        return self.http_response.text

    @property
    def xml(self) -> etree._Element:
        """The server's response as parsed XML."""
        return etree.XML(self.http_response.content, parser=XMLParser)

    def __repr__(self) -> str:
        return '<OAIResponse %s>' % self.params.get('verb')
