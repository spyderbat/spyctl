from typing import Dict, List
import yaml


class Fingerprint():
    def __init__(self, fprint) -> None:
        req_keys = ['spec', 'metadata', 'kind', 'apiVersion']
        for key in req_keys:
            if not key in fprint:
                raise KeyError(key)
        self.fprint = fprint
        if not 'name' in self.metadata:
            raise KeyError('metadata.name')
        self.suppr_str = ""
        self.calc_lengths()
    
    @property
    def metadata(self):
        return self.fprint['metadata']
    
    def get_id(self):
        return self.fprint.get('id')
    
    def preview_str(self, include_yaml=False):
        fprint_yaml = yaml.dump(dict(spec=self.fprint['spec']), sort_keys=False)
        return f"{self.metadata['name']}{self.suppr_str} --" + \
            f" proc_nodes: {self.fprint['proc_fprint_len']}," + \
            f" ingress_nodes: {self.fprint['ingress_len']}," + \
            f" egress_nodes: {self.fprint['egress_len']}" + \
            (f"|{fprint_yaml}" if include_yaml else "")
    
    def get_output(self):
        copy_fields = ['apiVersion', 'kind', 'spec', 'metadata']
        rv = dict()
        for key in copy_fields:
            rv[key] = self.fprint[key]
        return rv
    
    def set_num_suppressed(self, num: int):
        self.suppr_str = f" ({num} suppressed)"
    
    def calc_lengths(self):
        proc_fprint_len = 0
        node_queue = self.fprint['spec']['processPolicy'].copy()
        for node in node_queue:
            proc_fprint_len += 1
            if 'children' in node:
                node_queue += node['children']
        ingress_len = len(self.fprint['spec']['networkPolicy']['ingress'])
        egress_len = len(self.fprint['spec']['networkPolicy']['egress'])
        self.fprint['proc_fprint_len'] = proc_fprint_len
        self.fprint['ingress_len'] = ingress_len
        self.fprint['egress_len'] = egress_len
    
    @staticmethod
    def prepare_many(objs: List) -> List:
        latest: Dict[str, Fingerprint] = {}
        # keep only the latest fingerprints with the same id
        # can only filter out fingerprints that have ids, aka directly from the api
        ex_n = 0
        obj: Fingerprint
        for obj in objs:
            f_id = obj.get_id()
            if f_id is None:
                latest[ex_n] = obj
                ex_n += 1
                continue
            if f_id not in latest:
                latest[f_id] = obj
            elif latest[f_id].fprint['time'] < obj.fprint['time']:
                latest[f_id] = obj
        checksums = {}
        for obj in latest.values():
            checksum = obj.metadata['checksum']
            if checksum not in checksums:
                checksums[checksum] = {
                    'print': obj,
                    'suppressed': 0
                }
            else:
                entry = checksums[checksum]
                entry['suppressed'] += 1
                obj.set_num_suppressed(entry['suppressed'])
                entry['print'] = obj
        rv = [val['print'] for val in checksums.values()]
        rv.sort(key=lambda f: f.preview_str())
        return rv



def fingerprint_input(args):
    from cli import err_exit, read_stdin
    fingerprints = []
    def load_fprint(string):
        try:
            obj = yaml.load(string, yaml.Loader)
            if isinstance(obj, list):
                for o in obj:
                    fingerprints.append(Fingerprint(o))
            else:
                fingerprints.append(Fingerprint(obj))
        except yaml.YAMLError:
            err_exit("invalid yaml input")
        except KeyError as err:
            key, = err.args
            err_exit(f"fingerprint was missing key '{key}'")
    if len(args.files) == 0:
        inp = read_stdin()
        load_fprint(inp)
    else:
        for file in args.files:
            load_fprint(file.read())
    return fingerprints
    # return Fingerprint.prepare_many(fingerprints)
