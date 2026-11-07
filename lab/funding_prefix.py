"""Bounded model of pinned Lighter encoded funding, never an API cash decoder.

The source prefix is already price weighted. This adapter adds no second index
or rate factor. It models initialized positions only; it does not emulate a
circuit proof, trade cash flows, all margin rules, or a deployed account.
"""
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
import hashlib
import json

from lab.funding_values import clock_known
from lab.paper_account import PaperEvent
from lab.stream_quotes import FrameClock


SOURCE_TREE = '16c0f36d75f2306ee242e26e507e4c237f7f4074'
COLLATERAL_PER_USDC = 10**12
COLLATERAL_PER_MICRO_USDC = 10**6


def integer(value, bits, *, positive=False):
    if type(value) is not int or abs(value) >= 2**bits or (positive and value <= 0):
        raise ValueError('explicit integer outside conservative model domain')
    return value


def identity(value):
    if not isinstance(value, str) or not value or len(value) > 64 or any(ord(c) < 33 for c in value):
        raise ValueError('bounded nonblank identity required')
    return value


def multiplier(value):
    integer(value, 14, positive=True)
    if value > 10000:
        raise ValueError('quote multiplier exceeds received source maximum')
    return value


def market_strategy(market, strategy):
    # Source position slots0..254, not a public48-bit API market identifier.
    if type(market) is not int or not 0 <= market < 255:
        raise ValueError('explicit perpetual position-slot index0..254 required')
    if type(strategy) is not int or not 0 <= strategy < 8:
        raise ValueError('source strategy index0..7 required')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def collateral_usdc(value):
    integer(value, 96)
    with localcontext() as context:
        context.prec = 80
        return Decimal(value) / Decimal(COLLATERAL_PER_USDC)


@dataclass(frozen=True)
class PrefixPosition:
    account_id: str
    market_id: int
    strategy_index: int
    margin_mode: str
    size_units: int
    last_prefix: int
    quote_multiplier: int
    parameter_epoch: str
    initialized: bool
    last_update_ns: int
    clock: FrameClock
    source_tree: str = SOURCE_TREE

    def __post_init__(self):
        identity(self.account_id)
        identity(self.parameter_epoch)
        market_strategy(self.market_id, self.strategy_index)
        integer(self.size_units, 56)
        # Conservative subset: constants say62bits, comments63 and subtraction
        # uses64-bit limbs. This is not a claim to accept the full circuit domain.
        integer(self.last_prefix, 62)
        multiplier(self.quote_multiplier)
        if self.margin_mode not in ('cross', 'isolated') or type(self.initialized) is not bool:
            raise ValueError('explicit margin mode and initialized state required')
        if type(self.last_update_ns) is not int or self.last_update_ns < 0 or not isinstance(self.clock, FrameClock):
            raise ValueError('position economic update and first-seen clocks required')
        if self.last_update_ns > self.clock.utc_ns:
            raise ValueError('position update cannot follow its first receipt')
        if self.source_tree != SOURCE_TREE:
            raise ValueError('unreviewed source version')

    def bucket(self):
        suffix = 'cross' if self.margin_mode == 'cross' else 'isolated:' + str(self.market_id)
        return ('lighter-model:' + self.account_id + ':' + str(self.strategy_index) + ':' + suffix, 'USDC')


@dataclass(frozen=True)
class PrefixObservation:
    event_id: str
    market_id: int
    strategy_index: int
    prefix: int | None
    quote_multiplier: int
    parameter_epoch: str
    occurred_ns: int
    clock: FrameClock
    source_identity: str
    input_scope: str
    source_tree: str = SOURCE_TREE

    def __post_init__(self):
        for value in (self.event_id, self.parameter_epoch, self.source_identity):
            identity(value)
        market_strategy(self.market_id, self.strategy_index)
        if self.prefix is not None:
            integer(self.prefix, 62)
        multiplier(self.quote_multiplier)
        if type(self.occurred_ns) is not int or self.occurred_ns < 0 or not isinstance(self.clock, FrameClock):
            raise ValueError('economic and first-seen clocks required')
        if self.occurred_ns > self.clock.utc_ns:
            raise ValueError('prefix cannot be received before its declared economic observation')
        if self.input_scope not in ('invented_encoded_fixture', 'unverified_encoded_observation'):
            raise ValueError('raw API strings are not authenticated encoded state')
        if self.source_tree != SOURCE_TREE:
            raise ValueError('unreviewed source version')


def assess(position, observation, asof, anchor):
    """Exact algebra for supplied initialized encoded state, not paid funding."""
    if (not isinstance(position, PrefixPosition) or not isinstance(anchor, FrameClock)
            or type(asof) is not int or asof < 0):
        raise ValueError('typed position, anchor and as-of required')
    reasons = []
    if not position.initialized:
        reasons.append('position_initialization_unverified')
    if not clock_known(position.clock, asof, anchor):
        reasons.append('position_future_receipt_or_clock_step')
    if observation is None:
        reasons.append('encoded_prefix_missing')
    elif not isinstance(observation, PrefixObservation):
        raise ValueError('typed prefix observation required')
    else:
        if observation.prefix is None:
            reasons.append('encoded_prefix_missing')
        if (position.market_id, position.strategy_index) != (observation.market_id, observation.strategy_index):
            reasons.append('market_or_strategy_mismatch')
        if (position.parameter_epoch, position.quote_multiplier) != (observation.parameter_epoch, observation.quote_multiplier):
            reasons.append('parameter_epoch_or_multiplier_mismatch')
        if not clock_known(observation.clock, asof, anchor):
            reasons.append('future_receipt_or_clock_step')
        if anchor.utc_ns + asof - anchor.mono_ns < observation.occurred_ns:
            reasons.append('economic_observation_future')
        if observation.occurred_ns < position.last_update_ns or observation.clock.mono_ns < position.clock.mono_ns:
            reasons.append('prefix_precedes_position_state')
    amount = None
    if not reasons:
        difference = position.last_prefix - observation.prefix
        integer(difference, 64)
        amount = position.size_units * position.quote_multiplier * difference
        if abs(amount) >= 2**96:
            reasons.append('collateral_product_unrepresentable')
            amount = None
    return {'state': 'UNKNOWN' if reasons else 'MODEL_COLLATERAL', 'reasons': reasons,
            'collateral_delta': amount,
            'conditional_collateral_usdc': None if amount is None else str(collateral_usdc(amount)),
            'bucket': position.bucket(), 'source_tree': SOURCE_TREE,
            'cash_delta': None, 'api_units_verified': False, 'deployment_verified': False,
            'settled_cash_verified': False, 'actual_order_allowed': False}


def before_resize(position, observation, size_delta_units, asof, anchor, *, enabled=True):
    """Funding-only transition: OLD q accrues, checkpoint moves, THEN q changes.

    Fees, realized trading PnL, entry quote, margin transfers and initialization
    are deliberately outside this model. It cannot certify a complete trade.
    """
    integer(size_delta_units, 57)
    if not isinstance(position, PrefixPosition) or type(enabled) is not bool:
        raise ValueError('explicit enabled flag required')
    if not enabled:
        return {'state': 'DISABLED', 'next_position': position, 'assessment': None,
                'trade_cashflows_modeled': False, 'actual_order_allowed': False}
    result = assess(position, observation, asof, anchor)
    if observation is not None and observation.occurred_ns <= position.last_update_ns:
        result = {**result, 'state': 'UNKNOWN', 'collateral_delta': None,
                  'conditional_collateral_usdc': None,
                  'reasons': result['reasons'] + ['nonadvancing_funding_transition']}
    if result['collateral_delta'] is None:
        return {'state': 'UNKNOWN', 'next_position': None, 'assessment': result,
                'trade_cashflows_modeled': False, 'actual_order_allowed': False}
    new_size = integer(position.size_units + size_delta_units, 56)
    return {'state': 'MODEL_TRANSITION',
            'next_position': replace(position, size_units=new_size, last_prefix=observation.prefix,
                                     last_update_ns=observation.occurred_ns, clock=observation.clock),
            'assessment': result, 'trade_cashflows_modeled': False, 'actual_order_allowed': False}


def margin_component(old_collateral, funding_delta):
    """Declared Euclidean-floor model for one fixed-entry-quote margin component.

    Imported circuit division helpers/full aggregate route remain unverified.
    This is not a wallet credit and is never posted as another funding payment.
    """
    integer(old_collateral, 96)
    integer(funding_delta, 96)
    new_collateral = integer(old_collateral + funding_delta, 96)
    before = old_collateral // COLLATERAL_PER_MICRO_USDC
    after = new_collateral // COLLATERAL_PER_MICRO_USDC
    return {'old_component_micro_usdc': before, 'new_component_micro_usdc': after,
            'component_delta_micro_usdc': after - before,
            'conditional_collateral_usdc': str(collateral_usdc(funding_delta)),
            'wallet_credit_verified': False, 'full_aggregate_route_verified': False}


def paper_event(position, observation, assessment, asof, anchor):
    """Use the existing simulated ledger; only invented fixtures get model cash.

    Real/unverified encoded observations remain pending even if their algebra
    is computable. The conditional amount is not a decoder for Funding.value.
    Duplicate/revision handling and durable posting belong to PaperAccount.
    """
    if not isinstance(observation, PrefixObservation):
        raise ValueError('an observed economic event is required for a ledger record')
    expected = assess(position, observation, asof, anchor)
    if assessment != expected:
        raise ValueError('assessment does not bind this exact supplied state')
    amount = (expected['conditional_collateral_usdc']
              if observation.input_scope == 'invented_encoded_fixture' else None)
    venue, asset = position.bucket()
    # One start state can be consumed only once, even under renamed provider
    # events or an overlapping longer prefix interval. Changing its amount,
    # endpoint, size, mode or strategy then conflicts in the existing ledger.
    # A successful transition advances last_update_ns and gets a new start ID.
    event_id = 'prefix:' + digest([position.account_id, position.market_id, position.last_update_ns])
    binding = [SOURCE_TREE, position.parameter_epoch, position.quote_multiplier,
               position.strategy_index, position.margin_mode, position.size_units,
               position.last_prefix, position.initialized, observation.prefix,
               observation.parameter_epoch, observation.quote_multiplier,
               observation.strategy_index, observation.input_scope]
    return PaperEvent(event_id,
                      'funding', venue, asset, str(position.market_id), observation.occurred_ns,
                      observation.clock, 'source-model:' + digest(binding), amount=amount)
