"""Source timing diagnosis with invented metadata only."""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import audit_path_timing as a


class TimingAuditTests(unittest.TestCase):
    def tapes(self):
        t=np.arange(0,100_000_000,100_000,dtype=np.int64)
        b=pd.DataFrame(dict(t=t,off=np.zeros(len(t),dtype=np.int64),u=np.arange(len(t),dtype=np.int64)))
        q=pd.DataFrame(dict(t=t+50_000,off=np.zeros(len(t),dtype=np.int64),a=np.arange(len(t),dtype=np.int64)))
        return b,q

    def run_audit(self,b,q):
        grid=np.array([30_000_000,60_000_000],dtype=np.int64)
        with patch.object(a.rule,'decision_grid',return_value=(grid,grid)):
            return a.audit(b,q,'2026-10-29')

    def test_clean_metadata_has_no_future_failure(self):
        b,q=self.tapes();r=self.run_audit(b,q)
        self.assertEqual(r['counts']['timing_past_eligible'],2)
        self.assertEqual(r['counts']['future_any_timing_or_id_failure'],0)
        self.assertEqual(r['entry_wait_us']['max'],0)
        self.assertFalse(r['price_columns_loaded']);self.assertFalse(r['returns_computed'])

    def test_source_projection_refuses_price_fields(self):
        b,q=self.tapes();b['bid']=100
        with self.assertRaises(ValueError): self.run_audit(b,q)

    def test_future_clock_and_id_reasons_are_counted_without_prices(self):
        b,q=self.tapes();b.loc[310,'off']=2000;b.loc[315,'u']=300
        r=self.run_audit(b,q)
        self.assertEqual(r['counts']['future_offset_span'],1)
        self.assertEqual(r['counts']['future_nonincreasing_id'],1)
        self.assertEqual(r['counts']['future_any_timing_or_id_failure'],1)

    def test_next_quote_wait_is_distinct_from_clock_failure(self):
        b,q=self.tapes();b=b[~b.t.between(30_500_000,30_700_000)]
        r=self.run_audit(b,q)
        self.assertEqual(r['counts']['future_entry_wait'],1)
        self.assertEqual(r['counts']['future_offset_span'],0)
        self.assertEqual(r['entry_wait_us']['max'],300_000)

    def test_backwards_clock_is_not_sorted_into_an_apparent_result(self):
        b,q=self.tapes();b.loc[10,'t']=0
        r=self.run_audit(b,q)
        self.assertEqual(r['status'],'UNORDERED_RECEIVE_CLOCK')


if __name__=='__main__': unittest.main()
