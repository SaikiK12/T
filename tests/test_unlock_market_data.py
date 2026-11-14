import csv
import gzip
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

from scripts import unlock_market_data as d


def archive(name,rows):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        s=io.StringIO();w=csv.writer(s,lineterminator='\n');w.writerows(rows);z.writestr(name,s.getvalue())
    return b.getvalue()


class MarketDataTests(unittest.TestCase):
    def record(self,kind='fundingRate'):
        name='TESTUSDT-fundingRate-2021-01.zip' if kind=='fundingRate' else 'TESTUSDT-1d-2021-01.zip'
        return {'kind':kind,'symbol':'TESTUSDT','key':'a/'+name,'size':0}

    def test_funding_schema_preserves_exact_time_variable_interval_and_sign(self):
        r=self.record();b=archive(r['key'].split('/')[-1][:-4]+'.csv',[
            ['calc_time','funding_interval_hours','last_funding_rate'],[d.START,8,.0001],[d.START+3600001,1,-.0002]])
        self.assertEqual(d.parse(b,r),[(d.START,8.,.0001),(d.START+3600001,1.,-.0002)])

    def test_funding_invalid_reserved_nonfinite_and_duplicate_rows_fail(self):
        r=self.record();name=r['key'].split('/')[-1][:-4]+'.csv'
        for row in [[d.START-1,8,.001],[d.START,0,.001],[d.START,1.5,.001],[d.START,8,float('nan')],[d.START,8,2]]:
            with self.assertRaises(ValueError):d.parse(archive(name,[row]),r)
        with self.assertRaises(ValueError):d.parse(archive(name,[[d.START,8,.001]]*2),r)

    def test_mark_candle_is_not_traded_volume_and_requires_ms_ohlc(self):
        r=self.record('markPriceKlines');name=r['key'].split('/')[-1][:-4]+'.csv'
        row=[d.START,100,110,90,105,0,d.START+d.DAY-1,0,0,0,0,0]
        self.assertEqual(d.parse(archive(name,[row]),r),[(d.START,100.,110.,90.,105.)])
        for i,x in [(0,d.START*1000),(4,150),(6,d.START+d.DAY),(1,-1)]:
            bad=row.copy();bad[i]=x
            with self.assertRaises(ValueError):d.parse(archive(name,[bad]),r)

    def test_wrong_member_empty_and_oversized_csv_fail(self):
        r=self.record()
        for b in [archive('wrong.csv',[[d.START,8,.001]]),archive('TESTUSDT-fundingRate-2021-01.csv',[])]:
            with self.assertRaises(ValueError):d.parse(b,r)
        b=archive('TESTUSDT-fundingRate-2021-01.csv',[['x'*131073]])
        with self.assertRaises(ValueError):d.parse(b,r)

    def test_pair_verifies_publisher_hash_filename_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.record();b=archive('TESTUSDT-fundingRate-2021-01.csv',[[d.START,8,.001]]);r['size']=len(b)
            p=Path(tmp)/d.local_path(r);p.parent.mkdir();p.write_bytes(b)
            c=Path(str(p)+'.CHECKSUM');c.write_text(d.sha(b)+'  '+p.name+'\n')
            self.assertEqual(d.verify_pair(tmp,r)[0],b)
            c.write_text('0'*64+'  '+p.name+'\n')
            with self.assertRaises(ValueError):d.verify_pair(tmp,r)

    def test_pack_is_byte_deterministic_and_restore_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'file';p.write_bytes(b'raw primary bytes\n');pm=root/'manifest.json';pm.write_text('{}')
            files={'prices/data.zip':p,'prices/manifest.json':pm,'auxiliary/fundingRate/data.zip':p}
            with mock.patch.object(d,'verify'),mock.patch.object(d,'bundle_files',return_value=(files,{'meaning':'fixture'},[])),mock.patch.object(d.prereg,'verify',return_value='frozen'):
                d.pack(root,root,root/'one.tar.gz');d.pack(root,root,root/'two.tar.gz')
            self.assertEqual((root/'one.tar.gz').read_bytes(),(root/'two.tar.gz').read_bytes())
            result=d.restore(root/'one.tar.gz',root/'one.tar.gz.json',root/'restore')
            self.assertEqual(result['restored_files'],3)
            self.assertEqual((root/'restore/prices/data.zip').read_bytes(),p.read_bytes())
            with self.assertRaises(FileExistsError):d.restore(root/'one.tar.gz',root/'one.tar.gz.json',root/'restore')

    def test_restore_rejects_changed_blob_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'data';bundle.write_bytes(b'x');desc=root/'data.json';desc.write_text(json.dumps({'sha256':'0'*64}))
            with self.assertRaises(ValueError):d.restore(bundle,desc,root/'out')
            self.assertFalse((root/'out').exists())

    def test_restore_rejects_traversal_links_duplicate_and_unknown_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i,case in enumerate(['../escape','/absolute','prices/x','duplicate']):
                bundle=root/f'{i}.tar.gz'
                with tarfile.open(bundle,'w:gz') as t:
                    index=json.dumps({'../escape':{'sha256':d.sha(b'x'),'bytes':1}}).encode()
                    m=tarfile.TarInfo('BUNDLE_CONTENTS.json');m.size=len(index);t.addfile(m,io.BytesIO(index))
                    m=tarfile.TarInfo(case);m.size=1
                    if case=='prices/x':m.type=tarfile.SYMTYPE;m.linkname='/outside';m.size=0;t.addfile(m)
                    else:t.addfile(m,io.BytesIO(b'x'))
                    if case=='duplicate':t.addfile(m,io.BytesIO(b'x'))
                desc=root/f'{i}.json';desc.write_text(json.dumps({'sha256':d.sha(bundle.read_bytes())}))
                with self.assertRaises(ValueError):d.restore(bundle,desc,root/f'out{i}')
                self.assertFalse((root/f'out{i}').exists())

    def test_complete_manifest_is_never_overwritten_or_refetched(self):
        with tempfile.TemporaryDirectory() as tmp,mock.patch.object(d,'verify',return_value=('frozen',[])),mock.patch.object(d.source.Budget,'get') as get:
            Path(tmp,'manifest.json').write_text('{}')
            with self.assertRaises(FileExistsError):d.acquire(tmp)
            get.assert_not_called()
