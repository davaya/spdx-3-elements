"""
Create an SPDXv3 TransferUnit (document) from a set of element files
"""
import fire
import jadn
import json
import os
from urllib.parse import urlparse

SCHEMA = 'Schemas/spdx-v3.jidl'
DATA_DIR = 'Elements'
CONFIG_DIR = DATA_DIR + '/Config'
OUTPUT_DIR = 'Out'
DEFAULT_PROPERTIES = ('created', 'createdBy', 'specVersion', 'profile', 'dataLicense')
IRI_LOCATIONS = ['id', 'created/by', '*/elements/*', 'relationship/from', 'relationship/to/*',
                 '*/originator', 'elementRefs/id', 'annotation/subject']


def expand_iri(context: dict, element_id: str) -> str:
    """
    Convert an Element ID in namespace:local form to an IRI
    """
    if context:
        u = urlparse(element_id)
        if u.scheme:
            if prefix := context['prefixes'].get(u.scheme, ''):
                return prefix + u.path
            return element_id
        if element_id not in context.get('doc_ids', []):
            print(f'    Undefined Element: {element_id}')
        return context.get('namespace', '') + element_id
    return element_id


def compress_iri(context: dict, iri: str) -> str:
    """
    Convert an Element ID IRI to namespace:local form
    """
    if context:
        if base := context.get('namespace', ''):
            if iri.startswith(base):
                return iri.replace(base, '')
        for k, v in context.get('prefixes', {}).items():
            if iri.startswith(v):
                return iri.replace(v, k + ':')
    return iri


def expand_ids(context: dict, element: dict, paths: list) -> None:
    """
    Convert all IRIs in an element from namespace:local form to absolute IRI

    Hardcode IRI locations for now; replace with path-driven update
    """
    element.update({'id': expand_iri(context, element['id'])})
    if 'created' in element:
        element['created']['by'] = [expand_iri(context, k) for k in element['created']['by']]
    for etype, eprops in element['type'].items():
        for p in eprops:
            if p in ('elements', 'rootElements', 'originator', 'members'):
                eprops[p] = [expand_iri(context, k) for k in eprops[p]]
        if etype == 'annotation':
            eprops['subject'] = expand_iri(context, eprops['subject'])
        elif etype == 'relationship':
            eprops['from'] = expand_iri(context, eprops['from'])
            eprops['to'] = [expand_iri(context, k) for k in eprops['to']]


def compress_ids(context: dict, element: dict) -> None:
    """
    Convert all IRIs in an element from absolute IRI to namespace:local form

    Hardcode IRI locations for now; replace with path-driven update
    """
    element.update({'id': compress_iri(context, element['id'])})
    if 'created' in element:
        element['created']['by'] = [compress_iri(context, k) for k in element['created']['by']]
    for etype, eprops in element['type'].items():
        for p in eprops:
            if p in ('elements', 'rootElements', 'originator', 'members'):
                eprops[p] = [compress_iri(context, k) for k in eprops[p]]
        if etype == 'annotation':
            eprops['subject'] = compress_iri(context, eprops['subject'])
        elif etype == 'relationship':
            eprops['from'] = compress_iri(context, eprops['from'])
            eprops['to'] = [compress_iri(context, k) for k in eprops['to']]


def expand_element(context: dict, element: dict) -> dict:
    """
    Fill in Element properties from Context
    """
    element_x = {'id': ''}      # put id first
    element_x.update({k: context[k] for k in DEFAULT_PROPERTIES if k in context})
    element_x.update(element)
    expand_ids(context, element_x, IRI_LOCATIONS)
    return element_x


def compress_element(context: dict, element_x: dict) -> dict:
    element = {k: v for k, v in element_x.items() if v != context.get(k, '')}
    compress_ids(context, element)
    return element


def read_elements(dirname: str, codec):
    elements = []
    with os.scandir(dirname) as dir_items:
        for item in dir_items:
            if item.is_file() and os.path.splitext(item.name)[1] == '.json':
                with open(item.path) as fp:
                    element = codec.decode('Element', json.load(fp))
                elements.append(element)
    return elements


class TransferUnit():

    def make(self, config_file: str = 'baker-a1.json'):
        """
        Serialize individual elements into an SPDX file

        Config file:
          * namespace: base IRI for this file
          * namespaceMap: named IRI prefixes
          * include: elements to include, including subtree of all referenced elements
          * exclude: don't include specific elements from subtree
        """
        with open(os.path.join(CONFIG_DIR, config_file)) as tf:
            config = json.load(tf)
        with open(SCHEMA) as fp:
            schema = jadn.load_any(fp)
        codec = jadn.codec.Codec(schema, verbose_rec=True, verbose_str=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        elements = read_elements(DATA_DIR, codec)
        ex = {e['id']: e for e in elements}
        print(f'{len(elements)} elements read')

        sf = {'namespace': config['namespace']}
        nm = config.get('namespaceMap')
        sf.update({'namespaceMap': nm} if nm else {})

        with open(os.path.join(OUTPUT_DIR, config['filename']), 'w') as ofile:
            json.dump(sf, ofile, indent=2)

    def split(self, spdx_file: str):
        """
        Split an SPDX file into a list of independent elements
        """
        return

    def check(self, spdx_file: str):
        """
        Check an SPDX file

          * Element timestamps must be same as or before file timestamp
          * IRIs that are referenced but not listed in spdfDocumentRefs
          * IRIs without namespace prefixes
          * Duplicates in IRI sets
          * Root elements
        """
        return


if __name__ == '__main__':
    print(f'Installed JADN version: {jadn.__version__}\n')
    fire.Fire(TransferUnit)
