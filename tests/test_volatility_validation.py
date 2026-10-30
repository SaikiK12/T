import unittest
import numpy as np
import pandas as pd
from lab.volatility_validation import daily_returns,forecasts,loss,block_intervals,DAY,HOUR


class ForecastControlsTests(unittest.TestCase):
    def test_rv_target_and_no_future_in_ewma_or_mean(self):
        r=np.full(24*40,.01);y=np.sum(r.reshape(-1,24)**2,axis=1);p=forecasts(r,y)
        np.testing.assert_allclose(p[30],[.0024]*4)
        changed=r.copy();changed[31*24:]=99
        yy=np.sum(changed.reshape(-1,24)**2,axis=1)
        np.testing.assert_array_equal(forecasts(r,y)[:32],forecasts(changed,yy)[:32])

    def test_missing_volume_or_hour_is_not_zero_variance(self):
        t=np.arange(-HOUR,2*DAY,HOUR,dtype=np.int64);p=np.exp(np.arange(len(t))*.001)*100
        f=pd.DataFrame({'t':t,'close':p,'vol':1.})
        days,r,y=daily_returns(f,0,2*DAY);np.testing.assert_allclose(y,[.000024,.000024])
        f.loc[f.t==5*HOUR,'vol']=0
        self.assertTrue(np.isnan(daily_returns(f,0,2*DAY)[2][0]))
        f=f.loc[f.t!=25*HOUR];self.assertTrue(np.isnan(daily_returns(f,0,2*DAY)[2][1]))

    def test_qlike_zero_target_unit_scaling_and_invalid_forecast(self):
        y=np.array([0,.01,.1]);a=np.array([.01,.01,.05]);b=np.array([.02,.02,.1])
        self.assertTrue(np.isfinite(loss(y,a)).all())
        np.testing.assert_allclose(loss(y,a)-loss(y,b),loss(y*10000,a*10000)-loss(y*10000,b*10000))
        self.assertTrue(np.isnan(loss(1,0)));self.assertTrue(np.isnan(loss(np.nan,1)))

    def test_loss_uncertainty_keeps_family_and_serial_blocks(self):
        x=np.zeros((60,3));z=block_intervals(x,block=7,repetitions=100)
        self.assertEqual(z['lower'],[0,0,0]);self.assertEqual(z['upper'],[0,0,0])
        with self.assertRaises(ValueError):block_intervals(x,block=1)
        x[5,0]=np.nan
        with self.assertRaises(ValueError):block_intervals(x,block=14)

