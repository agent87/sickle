from typing import Dict, List, Iterator, Optional
from lxml import etree
from ._compat import PY3, to_str
from .utils import get_namespace, xml_to_dict
from .response import OAIResponse


class ResumptionToken:
    def __init__(self, token: str = '', cursor: str = '', complete_list_size: str = '',
                 expiration_date: str = '') -> None:
        self.token: str = token
        self.cursor: str = cursor
        self.complete_list_size: str = complete_list_size
        self.expiration_date: str = expiration_date

    def __repr__(self) -> str:
        return f'<ResumptionToken {self.token}>'


class OAIItem:
    def __init__(self, xml: etree._Element, strip_ns: bool = True) -> None:
        self.xml: etree._Element = xml
        self._strip_ns: bool = strip_ns
        self._oai_namespace: str = get_namespace(self.xml)

    def __bytes__(self) -> bytes:
        return etree.tounicode(self.xml).encode("utf8")

    def __str__(self) -> str:
        return self.__unicode__() if PY3 else self.__bytes__()

    def __unicode__(self) -> str:
        return etree.tounicode(self.xml)

    @property
    def raw(self) -> str:
        return etree.tounicode(self.xml)


class Identify(OAIItem):
    def __init__(self, identify_response: OAIResponse) -> None:
        super(Identify, self).__init__(identify_response.xml, strip_ns=True)
        self.xml = self.xml.find('.//' + self._oai_namespace + 'Identify')
        self._identify_dict: Dict[str, List[str]] = xml_to_dict(self.xml, strip_ns=True)
        for k, v in self._identify_dict.items():
            setattr(self, k.replace('-', '_'), v[0])

    def __repr__(self) -> str:
        return '<Identify>'

    def __iter__(self) -> Iterator[tuple]:
        return iter(self._identify_dict.items()) if PY3 else \
            self._identify_dict.iteritems()


class Header(OAIItem):
    def __init__(self, header_element: etree._Element) -> None:
        super(Header, self).__init__(header_element, strip_ns=True)
        self.deleted: bool = self.xml.attrib.get('status') == 'deleted'
        _identifier_element: Optional[etree._Element] = self.xml.find(self._oai_namespace + 'identifier')
        _datestamp_element: Optional[etree._Element] = self.xml.find(self._oai_namespace + 'datestamp')

        self.identifier: Optional[str] = getattr(_identifier_element, 'text', None)
        self.datestamp: Optional[str] = getattr(_datestamp_element, 'text', None)
        self.setSpecs: List[str] = [setSpec.text for setSpec in self.xml.findall(self._oai_namespace + 'setSpec')]

    def __repr__(self) -> str:
        if self.deleted:
            return f'<Header {self.identifier} [deleted]>'
        else:
            return f'<Header {self.identifier}>'

    def __iter__(self) -> Iterator[tuple]:
        return iter([
            ('identifier', self.identifier),
            ('datestamp', self.datestamp),
            ('setSpecs', self.setSpecs)
        ])


class Record(OAIItem):
    def __init__(self, record_element: etree._Element, strip_ns: bool = True) -> None:
        super(Record, self).__init__(record_element, strip_ns=strip_ns)
        self.header: Header = Header(self.xml.find(
            './/' + self._oai_namespace + 'header'))
        self.deleted: bool = self.header.deleted
        self.metadata: Optional[Dict[str, List[str]]] = None
        if not self.deleted:
            self.metadata = self.get_metadata()

    def __repr__(self) -> str:
        if self.header.deleted:
            return f'<Record {self.header.identifier} [deleted]>'
        else:
            return f'<Record {self.header.identifier}>'

    def __iter__(self) -> Iterator[tuple]:
        return iter(self.metadata.items()) if PY3 and self.metadata else \
            self.metadata.iteritems() if self.metadata else iter([])

    def get_metadata(self) -> Dict[str, List[str]]:
        metadata_element: Optional[etree._Element] = self.xml.find(
            './/' + self._oai_namespace + 'metadata')
        if metadata_element is not None and len(metadata_element.getchildren()) > 0:
            return xml_to_dict(metadata_element.getchildren()[0], strip_ns=self._strip_ns)
        return {}


class Set(OAIItem):
    def __init__(self, set_element: etree._Element) -> None:
        super(Set, self).__init__(set_element, strip_ns=True)
        self._set_dict: Dict[str, List[str]] = xml_to_dict(self.xml, strip_ns=True)
        for k, v in self._set_dict.items():
            setattr(self, k.replace('-', '_'), v[0])

    def __repr__(self) -> str:
        return f'<Set {to_str(self.setName)}>'

    def __iter__(self) -> Iterator[tuple]:
        return iter(self._set_dict.items()) if PY3 else \
            self._set_dict.iteritems()


class MetadataFormat(OAIItem):
    def __init__(self, mdf_element: etree._Element) -> None:
        super(MetadataFormat, self).__init__(mdf_element, strip_ns=True)
        self._mdf_dict: Dict[str, List[str]] = xml_to_dict(self.xml, strip_ns=True)
        for k, v in self._mdf_dict.items():
            setattr(self, k.replace('-', '_'), v[0])

    def __repr__(self) -> str:
        return f'<MetadataFormat {to_str(self.metadataPrefix)}>'

    def __iter__(self) -> Iterator[tuple]:
        return iter(self._mdf_dict.items()) if PY3 else \
            self._mdf_dict.iteritems()
