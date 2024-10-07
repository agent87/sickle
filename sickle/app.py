from typing import Dict, Type, Union, List, Optional, Any
import requests
from requests import Response
from .iterator import BaseOAIIterator, OAIItemIterator
from .response import OAIResponse
from .models import Set, Record, Header, MetadataFormat, Identify
import time

OAI_NAMESPACE = '{http://www.openarchives.org/OAI/%s/}'

DEFAULT_CLASS_MAP: Dict[str, Type[Union[Record, Header, Set, MetadataFormat, Identify]]] = {
    'GetRecord': Record,
    'ListRecords': Record,
    'ListIdentifiers': Header,
    'ListSets': Set,
    'ListMetadataFormats': MetadataFormat,
    'Identify': Identify,
}


class Sickle:
    def __init__(
        self,
        endpoint: str,
        http_method: str = 'GET',
        protocol_version: str = '2.0',
        iterator: Type[BaseOAIIterator] = OAIItemIterator,
        max_retries: int = 0,
        retry_status_codes: Optional[List[int]] = None,
        default_retry_after: int = 60,
        class_mapping: Optional[Dict[str, Type[Union[Record, Header, Set, MetadataFormat, Identify]]]] = None,
        encoding: Optional[str] = None,
        **request_args: Any
    ) -> None:
        self.endpoint: str = endpoint
        self.http_method: str = http_method
        self.protocol_version: str = protocol_version
        self.iterator: Type[BaseOAIIterator] = iterator
        self.max_retries: int = max_retries
        self.retry_status_codes: List[int] = retry_status_codes or [503]
        self.default_retry_after: int = default_retry_after
        self.oai_namespace: str = OAI_NAMESPACE % self.protocol_version
        self.class_mapping: Dict[str, Type[Union[Record, Header, Set, MetadataFormat, Identify]]] = class_mapping or DEFAULT_CLASS_MAP
        self.encoding: Optional[str] = encoding
        self.request_args: Dict[str, Any] = request_args

    def harvest(self, **kwargs: Any) -> OAIResponse:
        http_response: Response = self._request(kwargs)
        for _ in range(self.max_retries):
            if self._is_error_code(http_response.status_code) and http_response.status_code in self.retry_status_codes:
                retry_after: int = self.get_retry_after(http_response)
                time.sleep(retry_after)
                http_response = self._request(kwargs)
        http_response.raise_for_status()
        if self.encoding:
            http_response.encoding = self.encoding
        return OAIResponse(http_response, params=kwargs)

    def _request(self, kwargs: Dict[str, Any]) -> Response:
        if self.http_method == 'GET':
            return requests.get(self.endpoint, params=kwargs, **self.request_args)
        return requests.post(self.endpoint, data=kwargs, **self.request_args)

    def ListRecords(self, ignore_deleted: bool = False, **kwargs: Any) -> BaseOAIIterator:
        params: Dict[str, Any] = kwargs
        params.update({'verb': 'ListRecords'})
        return self.iterator(self, params, ignore_deleted=ignore_deleted)

    def ListIdentifiers(self, ignore_deleted: bool = False, **kwargs: Any) -> BaseOAIIterator:
        params: Dict[str, Any] = kwargs
        params.update({'verb': 'ListIdentifiers'})
        return self.iterator(self, params, ignore_deleted=ignore_deleted)

    def ListSets(self, **kwargs: Any) -> BaseOAIIterator:
        params: Dict[str, Any] = kwargs
        params.update({'verb': 'ListSets'})
        return self.iterator(self, params)

    def Identify(self) -> Identify:
        params: Dict[str, str] = {'verb': 'Identify'}
        return Identify(self.harvest(**params))

    def GetRecord(self, **kwargs: Any) -> Union[Record, Header, Set, MetadataFormat]:
        params: Dict[str, Any] = kwargs
        params.update({'verb': 'GetRecord'})
        record = next(self.iterator(self, params))
        return record

    def ListMetadataFormats(self, **kwargs: Any) -> BaseOAIIterator:
        params: Dict[str, Any] = kwargs
        params.update({'verb': 'ListMetadataFormats'})
        return self.iterator(self, params)

    def get_retry_after(self, http_response: Response) -> int:
        if http_response.status_code == 503:
            try:
                return int(http_response.headers.get('retry-after', self.default_retry_after))
            except TypeError:
                return self.default_retry_after
        return self.default_retry_after

    @staticmethod
    def _is_error_code(status_code: int) -> bool:
        return status_code >= 400
