from typing import Dict, Any, Optional, Iterator, Type
from sickle import oaiexceptions
from sickle.models import ResumptionToken
from sickle.app import Sickle
from sickle.response import OAIResponse
from xml.etree.ElementTree import Element

# Map OAI verbs to the XML elements
VERBS_ELEMENTS: Dict[str, str] = {
    'GetRecord': 'record',
    'ListRecords': 'record',
    'ListIdentifiers': 'header',
    'ListSets': 'set',
    'ListMetadataFormats': 'metadataFormat',
    'Identify': 'Identify',
}


class BaseOAIIterator:
    def __init__(self, sickle: Sickle, params: Dict[str, Any], ignore_deleted: bool = False) -> None:
        self.sickle: Sickle = sickle
        self.params: Dict[str, Any] = params
        self.ignore_deleted: bool = ignore_deleted
        self.verb: Optional[str] = self.params.get('verb')
        self.resumption_token: Optional[ResumptionToken] = None
        self.oai_response: OAIResponse
        self._next_response()

    def __iter__(self) -> 'BaseOAIIterator':
        return self

    def __next__(self) -> Any:
        return self.next()

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.verb}>'

    def _get_resumption_token(self) -> Optional[ResumptionToken]:
        resumption_token_element: Optional[Element] = self.oai_response.xml.find(
            './/' + self.sickle.oai_namespace + 'resumptionToken')
        if resumption_token_element is None:
            return None
        token: Optional[str] = resumption_token_element.text
        cursor: Optional[str] = resumption_token_element.attrib.get('cursor', None)
        complete_list_size: Optional[str] = resumption_token_element.attrib.get('completeListSize', None)
        expiration_date: Optional[str] = resumption_token_element.attrib.get('expirationDate', None)
        resumption_token = ResumptionToken(
            token=token, cursor=cursor,
            complete_list_size=complete_list_size,
            expiration_date=expiration_date
        )
        return resumption_token

    def _next_response(self) -> None:
        params: Dict[str, Any] = self.params
        if self.resumption_token:
            params = {
                'resumptionToken': self.resumption_token.token,
                'verb': self.verb
            }
        self.oai_response = self.sickle.harvest(**params)
        error: Optional[Element] = self.oai_response.xml.find(
            './/' + self.sickle.oai_namespace + 'error')
        if error is not None:
            code: str = error.attrib.get('code', 'UNKNOWN')
            description: str = error.text or ''
            try:
                raise getattr(oaiexceptions, code[0].upper() + code[1:])(description)
            except AttributeError:
                raise oaiexceptions.OAIError(description)
        self.resumption_token = self._get_resumption_token()

    def next(self) -> Any:
        raise NotImplementedError


class OAIResponseIterator(BaseOAIIterator):
    def next(self) -> OAIResponse:
        while True:
            if self.oai_response:
                response: OAIResponse = self.oai_response
                self.oai_response = None  # type: ignore
                return response
            elif self.resumption_token and self.resumption_token.token:
                self._next_response()
            else:
                raise StopIteration


class OAIItemIterator(BaseOAIIterator):
    def __init__(self, sickle: Sickle, params: Dict[str, Any], ignore_deleted: bool = False) -> None:
        self.mapper: Type[Any] = sickle.class_mapping[params.get('verb', '')]
        self.element: str = VERBS_ELEMENTS[params.get('verb', '')]
        self._items: Iterator[Element]
        super(OAIItemIterator, self).__init__(sickle, params, ignore_deleted)

    def _next_response(self) -> None:
        super(OAIItemIterator, self)._next_response()
        self._items = self.oai_response.xml.iterfind(
            './/' + self.sickle.oai_namespace + self.element)

    def next(self) -> Any:
        while True:
            for item in self._items:
                mapped: Any = self.mapper(item)
                if self.ignore_deleted and mapped.deleted:
                    continue
                return mapped
            if self.resumption_token and self.resumption_token.token:
                self._next_response()
            else:
                raise StopIteration
