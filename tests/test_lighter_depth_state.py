from copy import deepcopy
from decimal import Decimal
import unittest

from lab.executable_quotes import pair_costs
from lab.lighter_depth_state import LighterDepthState
from lab.microstructure import DepthLevel, DepthSnapshot
from lab.stream_quotes import FrameClock, NS, StreamBook

UTC=1_790_000_000*NS
CLOCK=FrameClock(UTC,10*NS)


def message(*,snapshot=False,begin=100,nonce=101,offset=11,stamp=UTC//1000,bids=None,asks=None):
    data={"code":0,"nonce":nonce,"offset":offset,"last_updated_at":stamp,
          "bids":bids if bids is not None else [],"asks":asks if asks is not None else []}
    if begin is not None:data["begin_nonce"]=begin
    return {"type":"subscribed/order_book" if snapshot else "update/order_book","channel":"order_book:1","order_book":data}


def snapshot():
    return message(snapshot=True,begin=None,nonce=100,offset=10,
                   bids=[{"price":"99","size":".1"},{"price":"98.5","size":"9"}],
                   asks=[{"price":"101","size":".1"},{"price":"101.5","size":"9"}])


def feed(s, payload, clock, *, epoch=None):
    """Synchronous fixture sends on its explicitly current test subscription."""
    return s.consume(payload, clock, epoch=s.epoch if epoch is None else epoch)


def state():
    s=LighterDepthState(1,"BTC");assert feed(s,snapshot(),CLOCK).status=="snapshot";return s


class DepthAssemblyTests(unittest.TestCase):
    def test_snapshot_is_sorted_exact_and_does_not_need_a_nonexistent_parent_nonce(self):
        s=state();b=s.as_stream_book()
        self.assertEqual((s.nonce,s.offset),(100,10))
        self.assertEqual([(x.price,x.size) for x in b.bids],[(99.,.1),(98.5,9.)])
        self.assertEqual(b.depth.exchange_time_ns,UTC)
        self.assertEqual(b.clock,CLOCK)

    def test_update_before_snapshot_and_replacement_without_reset_are_rejected(self):
        s=LighterDepthState(1,"BTC")
        self.assertEqual(feed(s,message(),CLOCK).status,"invalid")
        self.assertEqual(feed(s,snapshot(),CLOCK).status,"invalid")
        with self.assertRaises(ValueError):s.as_stream_book()
        s.reset();self.assertEqual(feed(s,snapshot(),CLOCK).status,"snapshot")
        self.assertEqual(feed(s,message(snapshot=True,nonce=200),CLOCK).status,"invalid")

    def test_linked_update_allows_skipped_offsets_and_replaces_absolute_size(self):
        s=state()
        result=feed(s,message(offset=1000,bids=[{"price":"99","size":".4"}]),CLOCK)
        self.assertTrue(result.changed)
        self.assertEqual((s.nonce,s.offset),(101,1000))
        self.assertEqual(s.as_stream_book().bids[0].size,.4)

    def test_zero_delete_unknown_tombstone_and_independent_level_map_oracle(self):
        s=state();oracle_b={Decimal('99'):Decimal('.1'),Decimal('98.5'):Decimal(9)}
        oracle_a={Decimal('101'):Decimal('.1'),Decimal('101.5'):Decimal(9)}
        changes=[('bids','99','0'),('asks','102','3'),('bids','98.5','4'),
                 ('asks','101','0'),('bids','98','2'),('asks','999','0')]
        for i,(side,p,q) in enumerate(changes):
            updates=[{"price":p,"size":q}]
            m=message(begin=100+i,nonce=101+i,offset=20+i*3,
                      bids=updates if side=='bids' else [],asks=updates if side=='asks' else [])
            feed(s,m,CLOCK)
            target=oracle_b if side=='bids' else oracle_a
            if Decimal(q):target[Decimal(p)]=Decimal(q)
            else:target.pop(Decimal(p),None)
            exported=s.as_stream_book()
            self.assertEqual([(Decimal(str(x.price)),Decimal(str(x.size))) for x in exported.bids],sorted(oracle_b.items(),reverse=True))
            self.assertEqual([(Decimal(str(x.price)),Decimal(str(x.size))) for x in exported.asks],sorted(oracle_a.items()))

    def test_nonce_gap_and_offset_regression_poison_without_partial_commit(self):
        for change in ({"begin":99},{"offset":10},{"nonce":99}):
            s=state();before=(s.nonce,s.offset,s._bids.copy())
            result=feed(s,message(bids=[{"price":"99","size":"8"}],**change),CLOCK)
            self.assertEqual(result.status,"invalid")
            self.assertEqual((s.nonce,s.offset,s._bids),before)
            with self.assertRaises(ValueError):s.as_stream_book()

    def test_malformed_second_side_or_crossed_candidate_is_atomic(self):
        for asks in ([{"price":"102","size":"NaN"}],[{"price":"98","size":"2"}],
                     [{"price":"102","size":"-1"}]):
            s=state();before=(s._bids.copy(),s._asks.copy(),s.nonce,s.offset)
            feed(s,message(bids=[{"price":"99","size":"4"}],asks=asks),CLOCK)
            self.assertEqual(s.status,"invalid")
            self.assertEqual((s._bids,s._asks,s.nonce,s.offset),before)

    def test_exact_retransmission_is_idempotent_before_nonce_link_check(self):
        s=state();m=message(bids=[{"price":"99","size":"2"}])
        feed(s,m,CLOCK)
        later=FrameClock(UTC+2*NS,CLOCK.mono_ns+2*NS)
        self.assertEqual(feed(s,deepcopy(m),later).status,"duplicate")
        self.assertEqual(s.last_state_clock,CLOCK)
        bad=deepcopy(m);bad['order_book']['bids'][0]['size']='3'
        self.assertEqual(feed(s,bad,later).status,"invalid")
        self.assertEqual(feed(s,m,later).status,"invalid")

    def test_keepalive_unrelated_market_empty_and_ineffective_batches_do_not_renew_freshness(self):
        s=state();later=FrameClock(UTC+3*NS,CLOCK.mono_ns+3*NS)
        self.assertEqual(feed(s,{"type":"pong"},later).status,"ignored")
        unrelated=message();unrelated['channel']='order_book:2'
        self.assertEqual(feed(s,unrelated,later).status,"ignored")
        self.assertEqual(feed(s,message(stamp=(UTC+3*NS)//1000),later).status,"no_effect")
        self.assertEqual((s.nonce,s.offset,s.last_state_clock),(101,11,later))
        self.assertEqual(s.liquidity_clock,CLOCK)
        self.assertIn('state_received_after_deadline',s.freshness_flags(CLOCK.mono_ns+NS//2,CLOCK))
        self.assertIn('receive_age_outside_0_1s',s.freshness_flags(later.mono_ns,CLOCK))
        self.assertIn('reported_source_age_outside_minus100ms_2s',s.freshness_flags(later.mono_ns,CLOCK))
        m=message(begin=101,nonce=102,offset=12,stamp=(UTC+3*NS)//1000,bids=[{"price":"99","size":".1"}])
        self.assertEqual(feed(s,m,later).status,'no_effect')
        self.assertEqual(s.liquidity_clock,CLOCK)
        s=state();stepped=FrameClock(UTC+1_200_000_000,CLOCK.mono_ns+200_000_000)
        feed(s,message(stamp=(UTC+200_000_000)//1000),stepped)
        self.assertIn('state_local_UTC_step_over_50ms',s.freshness_flags(CLOCK.mono_ns+300_000_000,CLOCK))

    def test_equal_nonce_noop_is_conservative_but_mutation_needs_progress(self):
        s=state();self.assertEqual(feed(s,message(nonce=100),CLOCK).status,'no_effect')
        self.assertEqual(s.nonce,100)
        s=state();self.assertEqual(feed(s,message(nonce=100,bids=[{"price":"99","size":"2"}]),CLOCK).status,'invalid')

    def test_known_clock_can_stay_equal_but_regression_and_wrong_units_fail(self):
        s=state();self.assertEqual(feed(s,message(bids=[{"price":"99","size":"2"}]),CLOCK).status,'updated')
        self.assertEqual(feed(s,message(begin=101,nonce=102,offset=12,stamp=UTC//1000-1),CLOCK).status,'invalid')
        s=state();self.assertEqual(feed(s,message(stamp=UTC//1_000_000),CLOCK).status,'invalid')
        s=state();m=message(bids=[{"price":"99","size":"2"}]);del m['order_book']['last_updated_at']
        self.assertEqual(feed(s,m,CLOCK).status,'invalid')
        with self.assertRaises(ValueError):s.as_stream_book()

    def test_numeric_booleans_duplicate_prices_and_missing_fields_are_not_plausible_depth(self):
        for field,value in (('nonce',True),('code',False),('offset',-1)):
            s=state();m=message();m['order_book'][field]=value
            self.assertEqual(feed(s,m,CLOCK).status,'invalid')
        for levels in ([{"price":"99","size":"1"},{"price":"99.0","size":"2"}],
                       [{"price":0,"size":"1"}],[{"price":"99","size":"1e9999"}]):
            s=state();self.assertEqual(feed(s,message(bids=levels),CLOCK).status,'invalid')
        s=state();m=message();del m['order_book']['begin_nonce']
        self.assertEqual(feed(s,m,CLOCK).status,'invalid')

    def test_capacity_is_never_silently_truncated_and_one_sided_book_is_unavailable(self):
        s=LighterDepthState(1,'BTC',max_levels=1)
        self.assertEqual(feed(s,snapshot(),CLOCK).status,'invalid')
        s=state();m=message(bids=[{"price":"99","size":"0"},{"price":"98.5","size":"0"}])
        self.assertEqual(feed(s,m,CLOCK).status,'updated')
        with self.assertRaises(ValueError):s.as_stream_book()

    def test_epoch_reset_accepts_another_server_offset_without_comparing_old_state(self):
        s=state();epoch=s.epoch;s.reset();self.assertEqual(s.epoch,epoch+1)
        with self.assertRaises(ValueError):s.as_stream_book()
        m=snapshot();m['order_book']['offset']=1
        self.assertEqual(feed(s,m,CLOCK).status,'snapshot')

    def test_missing_clock_cannot_erase_source_time_high_water_and_admit_a_regression(self):
        s=state();t=UTC//1000
        feed(s,message(stamp=t+1),CLOCK)
        self.assertEqual(s.reported_time_us,t+1)
        m=message(begin=101,nonce=102,offset=12);del m['order_book']['last_updated_at']
        self.assertEqual(feed(s,m,CLOCK).status,'invalid')
        self.assertEqual(s.reported_time_us,t+1)
        self.assertEqual(feed(s,message(begin=102,nonce=103,offset=13,stamp=t,bids=[{"price":"99","size":"2"}]),CLOCK).status,'invalid')

    def test_malformed_identity_error_and_disconnect_require_reset(self):
        for patch in ({'channel':None},{'channel':'invalid'},{'channel':'order_book:x'},
                      {'type':'error'},{'type':'shutdown'},{'type':'unsubscribed/order_book'},
                      {'type':None},{'type':['update/order_book']},{'type':'update/order_book_typo'}):
            s=state();m=message();m.update(patch)
            self.assertEqual(feed(s,m,CLOCK).status,'invalid')
            with self.assertRaises(ValueError):s.as_stream_book()
        s=state();s.invalidate('transport disconnected')
        with self.assertRaises(ValueError):s.as_stream_book()

    def test_saved_subscription_epoch_rejects_buffered_pre_reset_snapshots(self):
        s=state();old=s.epoch;new=s.reset()
        self.assertEqual(feed(s,snapshot(),CLOCK,epoch=old).status,'stale_epoch')
        with self.assertRaises(ValueError):s.as_stream_book()
        with self.assertRaises(TypeError):s.consume(snapshot(),CLOCK)
        self.assertEqual(feed(s,snapshot(),CLOCK,epoch=new).status,'snapshot')

    def test_existing_1x_2x_3x_cost_kernel_can_use_real_depth_without_borrowing_hidden_size(self):
        s=state();lt=s.as_stream_book()
        mx=StreamBook('mexc','BTC',CLOCK,
                      DepthSnapshot('BTC',UTC,CLOCK.mono_ns,(DepthLevel(99,10),),(DepthLevel(101,10),)),1,'synthetic')
        thin=StreamBook('lighter','BTC',CLOCK,
                        DepthSnapshot('BTC',UTC,CLOCK.mono_ns,lt.bids[:1],lt.asks[:1]),100,'synthetic BBO')
        self.assertFalse(pair_costs(mx,thin,1)['displayed_fillable'])
        costs=pair_costs(mx,lt,1)
        for tier,k in zip(costs['scenarios'],(1,2,3)):
            self.assertAlmostEqual(tier['round_trip_cost_usd'],5.18*k)
        self.assertEqual(costs['quantity_base'],1.)
        self.assertEqual(costs['capital_usd'],10000.)


if __name__=='__main__':unittest.main()
