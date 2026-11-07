"""Bounded structural decoder of pinned public MEXC spot-depth protobuf fields.

No guessed source clock or quantity units. Received source defines field tags,
but not the needed publication-unit/base-quantity/full-snapshot contracts.
Structural packets are not certified executable quotes or inferred fills.
"""
from dataclasses import asdict
from decimal import Decimal,InvalidOperation

from lab.stream_quotes import FrameClock

MAX_FRAME = 128*1024
PROTO_TREE = '0c9c4f35dd0fadc3a46a350e909a93379d81e811'


def varint(data, offset):
    value = 0
    for i in range(10):
        if offset >= len(data):raise ValueError('truncated protobuf varint')
        byte = data[offset];offset += 1
        if i == 9 and byte > 1:raise ValueError('protobuf integer exceeds64bits')
        value |= (byte&127) << (7*i)
        if not byte&128:return value,offset
    raise ValueError('overlong protobuf varint')


def fields(data):
    if type(data) is not bytes or len(data)>MAX_FRAME:raise ValueError('bounded binary protobuf required')
    result,offset = [],0
    while offset < len(data):
        if len(result)>=2048:raise ValueError('protobuf field-count bound')
        key,offset = varint(data,offset);number,wire = key>>3,key&7
        if not 0<number<2**29:raise ValueError('invalid protobuf field number')
        if wire == 0:value,offset = varint(data,offset)
        elif wire in (1,2,5):
            if wire == 2:size,offset = varint(data,offset)
            else:size = 8 if wire == 1 else 4
            if size>len(data)-offset:raise ValueError('truncated protobuf payload')
            value = data[offset:offset+size];offset += size
        else:raise ValueError('unsupported protobuf group/wire type')
        result.append((number,wire,value))
    return result


def one(items, number, wire, *, required=False):
    selected = [(w,v) for n,w,v in items if n==number]
    if len(selected)>1 or any(w!=wire for w,_ in selected):raise ValueError('duplicate/mistyped scalar protobuf field')
    if not selected:
        if required:raise ValueError('missing required structural protobuf field')
        return None
    return selected[0][1]


def string(value, *, required=False):
    if value is None:return None
    result = value.decode('utf8')
    if len(result)>256 or (required and not result) or any(ord(c)<32 for c in result):
        raise ValueError('unbounded/invalid protobuf string')
    return result


def signed64(value):
    if value is None:return None
    return value-2**64 if value>=2**63 else value


def level(raw):
    items = fields(raw)
    price = string(one(items,1,2,required=True),required=True)
    quantity = string(one(items,2,2,required=True),required=True)
    try:p,q = Decimal(price),Decimal(quantity)
    except InvalidOperation as exc:raise ValueError('numeric protobuf price/quantity required') from exc
    if not p.is_finite() or not q.is_finite() or not 0<p<=Decimal('1e30') or not 0<=q<=Decimal('1e30'):
        raise ValueError('unsupported price/quantity number')
    return price,quantity


def decode_depth(raw, clock):
    if not isinstance(clock,FrameClock):raise ValueError('original first-seen clock required')
    wrapper = fields(raw)
    channel = string(one(wrapper,1,2,required=True),required=True)
    return _decode_channel(wrapper,channel,clock)


def _decode_channel(wrapper, channel, clock):
    parts = channel.split('@')
    if len(parts)!=4 or parts[0]!='spot' or parts[1]!='public.limit.depth.v3.api.pb' or parts[3] not in ('5','10','20'):
        raise ValueError('explicit documented symbol/depth channel required')
    if not parts[2] or not parts[2].isascii() or not parts[2].isalnum() or parts[2]!=parts[2].upper():
        raise ValueError('uppercase spot symbol required')
    if any(n>=300 and n!=303 for n,_,_ in wrapper):
        raise ValueError('conflicting/unsupported wrapper payload type')
    payload = one(wrapper,303,2,required=True)
    body = fields(payload);limit = int(parts[3])
    asks,bids = [],[]
    for number,wire,value in body:
        if number in (1,2):
            if wire!=2:raise ValueError('mistyped depth item')
            (asks if number==1 else bids).append(level(value))
    if len(asks)>limit or len(bids)>limit:raise ValueError('payload exceeds subscribed depth')
    symbol = string(one(wrapper,3,2));symbol_id = string(one(wrapper,4,2))
    flags = ['source_timestamp_unit_unverified','quantity_asset_unit_unverified','full_snapshot_semantics_unverified']
    if symbol is None:flags.append('optional_symbol_not_received')
    elif symbol!=parts[2]:flags.append('channel_symbol_mismatch')
    if not asks or not bids:flags.append('one_side_or_both_sides_missing')
    if any(Decimal(q)==0 for _,q in asks+bids):flags.append('zero_quantity_snapshot_semantics_unknown')
    if any(Decimal(bids[i][0])<=Decimal(bids[i+1][0]) for i in range(len(bids)-1)):
        flags.append('bids_not_strictly_descending')
    if any(Decimal(asks[i][0])>=Decimal(asks[i+1][0]) for i in range(len(asks)-1)):
        flags.append('asks_not_strictly_ascending')
    if asks and bids and Decimal(bids[0][0])>=Decimal(asks[0][0]):flags.append('crossed_or_locked_book')
    send = signed64(one(wrapper,6,0))
    if send is None:flags.append('send_time_absent_no_fallback')
    return {'channel':channel,'subscription_symbol':parts[2],'symbol':symbol,'symbol_id':symbol_id,
            'first_seen':asdict(clock),'create_time_raw':signed64(one(wrapper,5,0)),
            'send_time_raw':send,'last_order_create_time_raw':signed64(one(body,5,0)),
            'event_type':string(one(body,3,2)),'version_raw':string(one(body,4,2)),
            'asks':asks,'bids':bids,'subscribed_levels':limit,'flags':flags,
            'proto_tree_identity':PROTO_TREE,'structural_depth_packet':True,
            'normalized_source_time_ns':None,'normalized_base_quantities':None,
            'executable_quote_eligible':False,'actual_order_allowed':False}
