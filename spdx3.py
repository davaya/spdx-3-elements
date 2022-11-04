"""
Create, merge, split, check or translate an SPDXv3 file (transfer unit)

Directories:
 * Elements - individual SPDXv3 elements
 * Elements/Config - configuration files defining elements to be serialized into an SpdxFile
 * Schemas - Syntax-agnostic schema defining the SpdxFile datatype
 * SpdxFiles - Serialized files (transfer units) containing multiple elements
 * Out - individual elements and SpdxFiles created by this script
"""
import fire
import jadn
import json
import os
from urllib.parse import urlparse

SCHEMA = 'Schemas/spdx-v3.jidl'
DATA_DIR = 'Elements'
OUTPUT_DIR = 'Out'
DEFAULT_PROPERTIES = ('creator', 'created', 'specVersion', 'profiles', 'dataLicense')
IRI_LOCATIONS = ['@id', 'created/by', '*/elements/*', 'relationship/from', 'relationship/to/*',
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
    element.update({'@id': expand_iri(context, element['@id'])})
    if 'creator' in element:
        # element['creator'] = [expand_iri(context, k) for k in [element['creator']]]
        element['creator'] = expand_iri(context, element['creator'])
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

    Add all IRIs in the element to context['ids']
    Hardcode IRI locations for now; replace with path-driven update
    """
    ids = [element['id']]
    element.update({'id': compress_iri(context, element['id'])})
    if 'creator' in element:
        ids += [element['creator']]
        # element['creator'] = [compress_iri(context, k) for k in [element['creator']]]
        element['creator'] = compress_iri(context, element['creator'])
    for etype, eprops in element['type'].items():
        for p in eprops:
            if p in ('elements', 'rootElements', 'originator', 'members'):
                ids += eprops[p]
                eprops[p] = [compress_iri(context, k) for k in eprops[p]]
        if etype == 'annotation':
            ids += eprops['subject']
            eprops['subject'] = compress_iri(context, eprops['subject'])
        elif etype == 'relationship':
            ids += [eprops['from']] + eprops['to']
            eprops['from'] = compress_iri(context, eprops['from'])
            eprops['to'] = [compress_iri(context, k) for k in eprops['to']]
    context['ids'] += ids


def expand_element(context: dict, element: dict) -> dict:
    """
    Fill in missing Element properties from context
    """
    element_x = {'@id': ''}      # put id first
    element_x.update({k: context[k] for k in DEFAULT_PROPERTIES if k in context})
    element_x.update(element)
    expand_ids(context, element_x, IRI_LOCATIONS)
    return element_x


def compress_element(context: dict, element_x: dict) -> dict:
    """
    Remove Element properties that exist in context
    """
    element = {k: v for k, v in element_x.items() if v != context.get(k, '')}
    compress_ids(context, element)
    return element


def read_elements(dirname: str, codec: jadn.codec.Codec):
    elements = []
    with os.scandir(dirname) as dir_items:
        for item in dir_items:
            if item.is_file() and os.path.splitext(item.name)[1] == '.json':
                elements.append(load_element(item.path, codec))
    return elements


def load_element(path: str, codec: jadn.codec.Codec) -> dict:
    with open(path) as fp:
        return codec.decode('Element', json.load(fp))


def load_codec() -> jadn.codec.Codec:
    with open(SCHEMA) as fp:
        schema = jadn.load_any(fp)
    return jadn.codec.Codec(schema, verbose_rec=True, verbose_str=True)


class SpdxFile():

    def make(self, config: str):
        """
        Make an SpdxDocument element that describes a serialized file

        CONFIG: JSON file that defines how to generate the SpdxDocument element:
          * namespace: base IRI for this file (rdf BASE)
          * prefixes: named IRI prefixes (rdf PREFIX)
          * creationInfo: element containing SPDX file creation info, not necessarily included in file
          * include: elements to include in SPDX file, including subtree of all referenced elements
          * exclude: don't include specific elements from subtree
          * fileRefs: SpdxDocument elements in spdxFileRefs
          * filename: SPDX file to create
        """
        with open(os.path.join(DATA_DIR, 'Config', config)) as cf:
            config = json.load(cf)
        codec = load_codec()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        elements = read_elements(DATA_DIR, codec)
        ex = {e['id']: e for e in elements}
        print(f'{len(elements)} elements read')
        ed = ex[config['creationInfo']]
        print(f'{ed["id"]}: Default creator {ed["creator"]} {ed["created"]}')

        sfile = {'namespace': config['namespace']}
        prefixes = config.get('prefixes')
        sfile.update({'prefixes': prefixes} if prefixes else {})
        sfile.update({k: ed[k] for k in DEFAULT_PROPERTIES})

        elist = config['include']
        while elist:
            sfile['ids'] = []
            sfile['elements'] = [ex[k]['id'] for k in elist]
            el = [k for k in sfile['ids'] if k not in elist]
            elist = el
        # sfile['creator'] = [compress_iri(sfile, k) for k in [sfile['creator']]]
        sfile['creator'] = compress_iri(sfile, sfile['creator'])
        del sfile['ids']

        with open(os.path.join(OUTPUT_DIR, config['filename']), 'w') as ofile:
            json.dump(sfile, ofile, indent=2)

    def merge(self, doc: str):
        """
        Merge a set of independent elements into an SPDX file (payload)

        DOC: SpdxDocument element that lists the elements to include in the SPDX file
        """
        codec = load_codec()
        element = load_element(doc, codec)

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
          * Display root elements
        """
        return


if __name__ == '__main__':
    print(f'Installed JADN version: {jadn.__version__}\n')
    fire.Fire(SpdxFile)
