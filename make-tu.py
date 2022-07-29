"""
Create an SPDXv3 TransferUnit (document) from a set of element files
"""
import fire
import jadn
import json
import os

SCHEMA = 'Schemas/spdx-v3.jidl'
DATA_DIR = 'Elements'
CONFIG_DIR = DATA_DIR + '/Config'
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

    def make(self, config_file: str = 'baker-a1.json'):

        with open(SCHEMA) as fp:
            schema = jadn.load_any(fp)
        codec = jadn.codec.Codec(schema, verbose_rec=True, verbose_str=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        elements = read_elements(DATA_DIR, codec)
        ex = {e['id']: e for e in elements}
        print(f'{len(elements)} elements read')
        with open(os.path.join(CONFIG_DIR, config_file)) as tf:
            config = json.load(tf)

        sf = {'namespace': config['namespace']}
        nm = config.get('namespaceMap')
        sf.update({'namespaceMap': nm} if nm else {})

        with open(os.path.join(OUTPUT_DIR, config['filename']), 'w') as ofile:
            json.dump(sf, ofile, indent=2)

    def split(self, spdx_file: str):
        return

    def check(self, spdx_file: str):
        return


if __name__ == '__main__':
    print(f'Installed JADN version: {jadn.__version__}\n')
    fire.Fire(TransferUnit)
