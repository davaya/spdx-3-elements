"""
Create an SPDXv3 TransferUnit (document) from a set of element files
"""
import fire
import jadn
import json
import os

SCHEMA = 'Schemas/spdx-v3.jidl'
DATA_DIR = 'Elements'
TEMPLATE_DIR = DATA_DIR + '/Templates'
OUTPUT_DIR = 'Out'


def read_elements(dirname: str, codec):
    elements = []
    with os.scandir(dirname) as it:
        for entry in it:
            if entry.is_file() and os.path.splitext(entry.name)[1] == '.json':
                with open(entry.path) as fp:
                    element = codec.decode('Element', json.load(fp))
                elements.append(element)
    return elements


class TransferUnit():

    def make(self, template_file: str = 'baker-a1.json'):

        with open(SCHEMA) as fp:
            schema = jadn.load_any(fp)
        codec = jadn.codec.Codec(schema, verbose_rec=True, verbose_str=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        elements = read_elements(DATA_DIR, codec)
        with open(os.path.join([TEMPLATE_DIR, template_file])) as tf:
            template = json.load(tf)

        tu = {'namespace': template['namespace']}
        nm = template.get('namespaceMap')
        tu.update({'namespaceMap': nm} if nm else {})

    def split(self, spdx_file: str):
        return


if __name__ == '__main__':
    print(f'Installed JADN version: {jadn.__version__}\n')
    fire.Fire(TransferUnit)
