"""R326 scope over the frozen raw rational oracle; no input acquisition."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.check_spot_costs import audit as parent_audit


def audit(result):
    r=json.loads(Path(result).read_text())
    if r['registry_id']!='R326' or r['parent_raw_registry_id']!='R325' or r['new_market_requests']!=0:
        raise ValueError('same-data repair scope mismatch')
    return {**parent_audit(result),'registry_id':'R326','parent_raw_registry_id':'R325',
            'new_market_requests':0,'parent_failed_result_preserved':True}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('result',type=Path)
    print(json.dumps(audit(p.parse_args().result),sort_keys=True,indent=2))
