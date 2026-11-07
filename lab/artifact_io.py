"""Content-bound local table cache and verified immutable Parquet export.

Never fetches data, overwrites a source, unpickles objects or caches a successful
test/gate label. Every hit still hashes current source bytes. Callers receive
independent frames so mutation cannot change another study's input.
"""
from collections import OrderedDict
import hashlib
import io
import json
import re
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def read_bytes(path,limit=32*1024**2):
    p=Path(path)
    if any(x.is_symlink() for x in (p,*p.absolute().parents)) or not p.is_file() or not 0<p.stat().st_size<=limit:raise ValueError('bounded regular table input required')
    with p.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('table grew beyond declared bound')
    return raw,hashlib.sha256(raw).hexdigest()


class ContentFrameCache:
    def __init__(self,*,max_frame_bytes=8*1024**2,max_items=8):
        if type(max_frame_bytes) is not int or max_frame_bytes<=0 or type(max_items) is not int or max_items<=0:
            raise ValueError('positive finite cache limits required')
        self.max_bytes,self.max_items=max_frame_bytes,max_items
        self.frames=OrderedDict();self.bytes=0;self.hits=0;self.misses=0

    def load(self,path,*,columns=None,expected_sha256=None):
        raw,digest=read_bytes(path)
        if expected_sha256 is not None and digest!=expected_sha256:raise ValueError('source content identity changed')
        key=(str(Path(path).resolve()),digest,tuple(columns) if columns is not None else None,pd.__version__,pa.__version__)
        hit=key in self.frames
        if hit:
            self.hits+=1;frame,size=self.frames.pop(key);self.frames[key]=(frame,size)
        else:
            self.misses+=1;frame=pd.read_parquet(io.BytesIO(raw),columns=columns)
            for c in frame.select_dtypes(include='object'):
                if any(not isinstance(x,(str,int,float,bool,type(None))) for x in frame[c]):raise ValueError('mutable nested cells cannot be cached as independent inputs')
            size=int(frame.memory_usage(index=True,deep=True).sum())
            if size<=self.max_bytes:
                while self.frames and (self.bytes+size>self.max_bytes or len(self.frames)>=self.max_items):
                    _,(_,old)=self.frames.popitem(last=False);self.bytes-=old
                self.frames[key]=(frame,size);self.bytes+=size
        return frame.copy(deep=True),{'source_sha256':digest,'cache_hit':hit,
            'cache_hits':self.hits,'cache_misses':self.misses,'resident_frame_bytes':self.bytes,
            'scope':'table cache only; no outcome/test/gate cache'}


def export_verified(frame,path,*,source_sha256,price_role,clock_role):
    if not isinstance(source_sha256,str) or not re.fullmatch('[0-9a-f]{64}',source_sha256):raise ValueError('explicit source digest required')
    if not price_role or not clock_role:raise ValueError('explicit price and clock roles required')
    p=Path(path)
    if p.exists() or p.is_symlink():raise ValueError('new immutable derived path required')
    table=pa.Table.from_pandas(frame,preserve_index=False)
    meta=dict(table.schema.metadata or {});meta[b'quant_lab_provenance']=json.dumps({
        'source_sha256':source_sha256,'price_role':price_role,'clock_role':clock_role,
        'source_untouched':True,'scope':'format export, not new observations'},sort_keys=True).encode()
    table=table.replace_schema_metadata(meta)
    buffer=pa.BufferOutputStream();pq.write_table(table,buffer,compression='zstd',compression_level=3)
    raw=buffer.getvalue().to_pybytes()
    reread=pq.read_table(pa.BufferReader(raw))
    pd.testing.assert_frame_equal(frame.reset_index(drop=True),reread.to_pandas(),check_exact=True,check_dtype=True)
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as stream:stream.write(raw)
    return {'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'rows':len(frame),
            'columns':list(frame.columns),'source_sha256':source_sha256,'roundtrip_exact':True,
            'price_role':price_role,'clock_role':clock_role,'native_memory_measured':False}
