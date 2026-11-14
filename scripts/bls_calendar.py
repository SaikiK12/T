"""Restricted BLS iCalendar reader: announced schedules, not actual releases.

Unfolds content lines and preserves UID revisions. Recurring VEVENTs and
malformed calendars fail the whole poll. Floating, date-only and ambiguous
clocks remain unknown rather than being silently assigned Eastern/UTC.
"""
from datetime import datetime,timezone
import re
from zoneinfo import ZoneInfo

NY=ZoneInfo('America/New_York')
MAX_BYTES=2*1024**2
FIELDS={
    'title':'SUMMARY','dtstart':'DTSTART','tzid':'DTSTART;TZID','value_type':'DTSTART;VALUE',
    'schedule_day':'DTSTART (Eastern calendar date, derived)','clock_state':'DTSTART (clock classification)',
    'sequence':'SEQUENCE','status':'STATUS','dtstamp':'DTSTAMP','last_modified':'LAST-MODIFIED',
    'description':'DESCRIPTION',
}


def split_quoted(text,separator):
    out=[];start=0;quoted=False
    for i,c in enumerate(text):
        if c=='"': quoted=not quoted
        if c==separator and not quoted:
            out.append(text[start:i]);start=i+1
    if quoted: raise ValueError('BLS ICS: unbalanced parameter quotes')
    out.append(text[start:]);return out


def content_line(line):
    quoted=False;cut=None
    for i,c in enumerate(line):
        if c=='"': quoted=not quoted
        if c==':' and not quoted: cut=i;break
    if cut is None: raise ValueError('BLS ICS: invalid content line')
    header,value=line[:cut],line[cut+1:]
    parts=split_quoted(header,';');name=parts[0].upper();params={}
    for part in parts[1:]:
        if '=' not in part: raise ValueError('BLS ICS: invalid parameter')
        k,v=part.split('=',1);k=k.upper()
        if k in params: raise ValueError('BLS ICS: duplicate parameter')
        params[k]=v.removeprefix('"').removesuffix('"')
    return name,params,value


def text_value(value):
    def replace(match):
        c=match.group(1)
        if c in ('n','N'): return '\n'
        if c in ('\\',',',';'): return c
        raise ValueError('BLS ICS: unsupported text escape')
    if value.endswith('\\') and len(value)-len(value.rstrip('\\')) & 1:
        raise ValueError('BLS ICS: incomplete text escape')
    return re.sub(r'\\(.)',replace,value)


def start_time(value,params):
    kind=params.get('VALUE','DATE-TIME').upper();zone=params.get('TZID','')
    if kind=='DATE':
        if not re.fullmatch(r'\d{8}',value): raise ValueError('BLS ICS: invalid DATE')
        day=datetime.strptime(value,'%Y%m%d').date().isoformat()
        return day,'','date_only'
    if kind!='DATE-TIME' or not re.fullmatch(r'\d{8}T\d{6}Z?',value):
        raise ValueError('BLS ICS: unsupported DTSTART')
    d=datetime.strptime(value.rstrip('Z'),'%Y%m%dT%H%M%S')
    if value.endswith('Z'):
        if zone: raise ValueError('BLS ICS: UTC value also declares TZID')
        aware=d.replace(tzinfo=timezone.utc)
    elif zone in ('US-Eastern','US/Eastern','America/New_York'):
        possible={d.replace(tzinfo=NY,fold=fold).astimezone(timezone.utc) for fold in (0,1)
                  if d.replace(tzinfo=NY,fold=fold).astimezone(timezone.utc).astimezone(NY).replace(tzinfo=None)==d}
        if len(possible)!=1: return d.date().isoformat(),'','ambiguous_or_nonexistent'
        aware=possible.pop()
    elif zone in ('UTC','Etc/UTC'):
        aware=d.replace(tzinfo=timezone.utc)
    else:
        return d.date().isoformat(),'','floating' if not zone else 'unknown_timezone'
    return (aware.astimezone(NY).date().isoformat(),
            aware.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'scheduled_clock')


def parse(raw,from_day):
    """Return complete items on/after from_day (an Eastern calendar date)."""
    datetime.strptime(from_day,'%Y-%m-%d')
    if not isinstance(raw,bytes) or len(raw)>MAX_BYTES: raise ValueError('BLS ICS: bounded bytes required')
    lines=[]
    for line in raw.decode('utf-8-sig').splitlines():
        if line.startswith((' ','\t')):
            if not lines: raise ValueError('BLS ICS: orphan folded line')
            lines[-1]+=line[1:]
        elif line: lines.append(line)
    if not lines or lines[0].upper()!='BEGIN:VCALENDAR' or lines[-1].upper()!='END:VCALENDAR':
        raise ValueError('BLS ICS: complete VCALENDAR required')
    stack=[];events=[];current=None;calendar_seen=False
    for line in lines:
        name,params,value=content_line(line)
        if name=='BEGIN':
            component=value.upper()
            if not stack and component!='VCALENDAR': raise ValueError('BLS ICS: invalid root')
            if component=='VCALENDAR':
                if stack or calendar_seen: raise ValueError('BLS ICS: multiple calendars')
                calendar_seen=True
            if component=='VEVENT':
                if stack!=['VCALENDAR'] or current is not None: raise ValueError('BLS ICS: nested event')
                current={}
            stack.append(component);continue
        if name=='END':
            if not stack or stack[-1]!=value.upper(): raise ValueError('BLS ICS: component mismatch')
            if stack[-1]=='VEVENT': events.append(current);current=None
            stack.pop();continue
        if not stack: raise ValueError('BLS ICS: content outside calendar')
        if stack[-1]!='VEVENT': continue
        if name in ('RRULE','RDATE','EXDATE','RECURRENCE-ID'):
            raise ValueError('BLS ICS: recurring event unsupported')
        if name in ('UID','DTSTART','SUMMARY','SEQUENCE','STATUS','DTSTAMP','LAST-MODIFIED','DESCRIPTION'):
            if name in current: raise ValueError('BLS ICS: duplicate event field')
            current[name]=(params,value)
    if stack or current is not None or not events: raise ValueError('BLS ICS: empty or incomplete event list')
    out={};seen=set()
    for e in events:
        if any(k not in e for k in ('UID','DTSTART','SUMMARY')): raise ValueError('BLS ICS: event identity/start/title missing')
        uid=text_value(e['UID'][1]).strip()
        if not uid or len(uid)>512 or any(ord(c)<32 for c in uid) or uid in seen:
            raise ValueError('BLS ICS: invalid/duplicate UID')
        seen.add(uid)
        params,value=e['DTSTART'];day,utc,state=start_time(value,params)
        title=text_value(e['SUMMARY'][1]).strip()
        if not title: raise ValueError('BLS ICS: empty title')
        if day<from_day: continue
        fields=dict(title=title,dtstart=value,tzid=params.get('TZID',''),value_type=params.get('VALUE','DATE-TIME'),
                    schedule_day=day,clock_state=state)
        for field,source in (('sequence','SEQUENCE'),('status','STATUS'),('dtstamp','DTSTAMP'),
                             ('last_modified','LAST-MODIFIED'),('description','DESCRIPTION')):
            fields[field]=text_value(e.get(source,({},''))[1])
        out[uid]={'fields':fields,'etime':('DTSTART (scheduled, not actual publication)',value,utc)}
    return out
