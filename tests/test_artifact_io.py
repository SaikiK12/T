from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from lab.artifact_io import ContentFrameCache,read_bytes,export_verified


class ArtifactIOTests(unittest.TestCase):
    def test_content_change_and_caller_mutation_cannot_reuse_wrong_values(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.parquet';pd.DataFrame({'t':[1,2],'price':[10.,np.nan]}).to_parquet(p,index=False)
            c=ContentFrameCache();a,one=c.load(p);a.loc[0,'price']=999
            b,two=c.load(p);self.assertEqual(b.loc[0,'price'],10);self.assertEqual(two['cache_hits'],1)
            digest=one['source_sha256'];pd.DataFrame({'t':[1,2],'price':[20.,np.nan]}).to_parquet(p,index=False)
            with self.assertRaises(ValueError):c.load(p,expected_sha256=digest)
            b,three=c.load(p);self.assertEqual(b.loc[0,'price'],20);self.assertEqual(three['cache_misses'],2)
            self.assertFalse(three['cache_hit']);self.assertTrue(two['cache_hit'])

    def test_parquet_export_preserves_missing_values_clocks_types_and_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.parquet';f=pd.DataFrame({'t':np.array([1790000000000000000,1790000000000000001],dtype='int64'),'price':[1.,np.nan]})
            f.to_parquet(source,index=False);prefix=source.read_bytes();raw,digest=read_bytes(source)
            out=Path(d)/'derived.parquet';r=export_verified(f,out,source_sha256=digest,price_role='trade_close',clock_role='source_bar_end_not_first_seen')
            self.assertTrue(r['roundtrip_exact']);self.assertEqual(source.read_bytes(),prefix)
            self.assertIn(b'quant_lab_provenance',pq.read_schema(out).metadata)
            with self.assertRaises(ValueError):export_verified(f,out,source_sha256=digest,price_role='x',clock_role='y')

    def test_bounded_cache_evicts_and_source_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.parquet',Path(d)/'b.parquet';pd.DataFrame({'x':[1]}).to_parquet(a,index=False);pd.DataFrame({'x':[2]}).to_parquet(b,index=False)
            c=ContentFrameCache(max_items=1);c.load(a);c.load(b);self.assertEqual(len(c.frames),1)
            link=Path(d)/'alias.parquet';link.symlink_to(a)
            with self.assertRaises(ValueError):c.load(link)

