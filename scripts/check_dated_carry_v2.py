"""R328 label/lineage wrapper around the frozen independent R327 raw oracle."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.check_dated_carry import audit as parent_audit


def audit(path):
    result=json.loads(Path(path).read_text())
    if (result['registry_id']!='R328' or result['parent_raw_registry_id']!='R327'
            or result['new_market_requests']!=0):raise ValueError('wrong same-data repair scope')
    checked=parent_audit(path)
    checked['registry_id']='R328';checked['parent_raw_registry_id']='R327'
    return checked


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('result',type=Path)
    args=p.parse_args();value=audit(args.result)
    with (args.result.parent/'audit.json').open('x') as h:h.write(json.dumps(value,sort_keys=True,indent=2)+'\n')
    print(json.dumps(value,sort_keys=True))
