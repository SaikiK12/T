"""What traders with a proven record say about where their money came from (owner, 2026-10-21: "they can at a time make
a mistake on words or phrasing that lets us infer how they proceed"). Reading notes in docs/TRADER_TALKS.md.

The podcast index of scripts/dig_podcasts.py (data/videos/episodes.csv, 42 feeds) is searched for the people of ROSTER;
their episodes are turned into text (the feed's transcript, else local faster-whisper on the audio, French with the
multilingual "small" model), and every transcript is cut into windows around CUES: the phrases people use when they
say how a trade made money ("most of our money", "the other side", "we were the only ones", "forced sellers",
"rebate"...). The windows are ranked for reading; nothing is computed on market data.

Tiers (how far a person's results can be checked, not how good they sound):
- A: results checked by a third party: audited fund or CTA records, public filings, a court or regulator record, an
  audited trading competition.
- B: a documented career at a known firm, or results widely reported, but the numbers are the person's own.
- C: results shown only by the person, or income that comes mainly from courses, signals or prop-firm challenges.

Steps:
1. `match`: episodes whose title names a roster person (or whose summary does, kept apart) -> data/videos/talks.csv.
2. `fetch`: text for the matched episodes, feed transcripts first; with --whisper-python, up to --max-hours of audio
   are transcribed, tier A first and the person named in the title first. Text goes to data/videos/subs/pod_<key>.txt
   (shared with dig_podcasts.py, so a transcript is made once).
3. `cues`: windows of WINDOW words around cue hits in every fetched transcript of a roster episode, scored; the top
   windows per person -> data/videos/talk_cues.jsonl and data/videos/talk_cues.md (for reading).

data/ is gitignored. Paper research only.

usage: python scripts/dig_talks.py match
       python scripts/dig_talks.py fetch [--whisper-python PATH --tmp DIR --max-hours 20] [--people REGEX]
       python scripts/dig_talks.py cues [--per-person 12]
"""
import argparse
import bisect
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dig_podcasts as dp  # noqa: E402

OUT = ROOT / "data" / "videos"
SUBS = OUT / "subs"
WINDOW = 140                                        # words on each side of a cue hit
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

# (name, regex on titles and summaries, tier, domain, why the tier)
ROSTER = [
    # quant and systematic funds
    ("Jim Simons", r"\bJim Simons\b|\bJames Simons\b", "A", "quant fund", "Medallion returns reported by investors and Zuckerman's book"),
    ("Robert Frey", r"\bRobert Frey\b", "B", "quant fund", "ex-Renaissance partner"),
    ("Nick Patterson", r"\bNick Patterson\b", "B", "quant fund", "ex-Renaissance researcher"),
    ("Ed Thorp", r"\bEd(ward)? (O\. )?Thorp\b", "A", "quant fund", "Princeton Newport's audited record"),
    ("Cliff Asness", r"\bCliff(ord)? Asness\b", "A", "quant fund", "AQR's public fund returns"),
    ("David Harding", r"\bDavid Harding\b", "A", "CTA", "Winton's audited record"),
    ("Peter Muller", r"\bPeter Muller\b", "B", "quant fund", "ran Morgan Stanley's PDT"),
    ("Rob Carver", r"\bRob(ert)? Carver\b", "B", "CTA", "ex-AHL portfolio manager"),
    ("Andreas Clenow", r"\bAndreas Clenow\b", "B", "CTA", "ran a fund; own figures"),
    ("Jeff Yass", r"\bJeff(rey)? Yass\b", "A", "options market maker", "co-founder of Susquehanna (SIG)"),
    # macro and discretionary funds
    ("Paul Tudor Jones", r"\bPaul Tudor Jones\b|\bTudor Jones\b", "A", "macro fund", "Tudor's audited record"),
    ("Stanley Druckenmiller", r"\bDruckenmiller\b", "A", "macro fund", "Duquesne's audited record"),
    ("George Soros", r"\bGeorge Soros\b", "A", "macro fund", "Quantum Fund's audited record"),
    ("Ray Dalio", r"\bRay Dalio\b", "A", "macro fund", "Bridgewater's audited record"),
    ("Bill Lipschutz", r"\bBill Lipschutz\b", "B", "FX", "Salomon FX desk (Schwager interview)"),
    ("John Arnold", r"\bJohn Arnold\b", "A", "energy", "Enron gas desk and Centaurus"),
    ("Steve Cohen", r"\bSteve(n)? (A\. )?Cohen\b", "A", "equity fund", "SAC and Point72"),
    ("Michael Platt", r"\bMichael Platt\b", "A", "macro fund", "BlueCrest"),
    # individual and competition traders
    ("Linda Raschke", r"\bLinda (Bradford )?Raschke\b", "A", "futures", "registered CTA; Schwager's New Market Wizards"),
    ("Peter Brandt", r"\bPeter (L\. )?Brandt\b", "A", "futures", "registered CTA; Schwager's Unknown Market Wizards"),
    ("Ed Seykota", r"\bEd Seykota\b|\bSeykota\b", "B", "futures", "Schwager's Market Wizards; client records not public"),
    ("Mark Minervini", r"\bMark Minervini\b", "A", "stocks", "won the 1997 US Investing Championship (audited)"),
    ("David Ryan", r"\bDavid Ryan\b", "A", "stocks", "won the US Investing Championship three times"),
    ("Marty Schwartz", r"\bMarty Schwartz\b", "A", "futures", "won the US Trading Championship"),
    ("Larry Williams", r"\bLarry Williams\b", "A", "futures", "won the 1987 Robbins World Cup (audited)"),
    ("Andrea Unger", r"\bAndrea Unger\b", "A", "futures", "won the World Cup Trading Championship four times"),
    ("Kevin Davey", r"\bKevin Davey\b", "A", "futures", "placed in the World Cup Trading Championship"),
    ("Tom Hougaard", r"\bTom Hougaard\b", "B", "index CFDs", "publishes his trades; own figures"),
    ("Takashi Kotegawa (BNF)", r"\bKotegawa\b|\bBNF\b", "A", "Japanese stocks", "the 2005 J-Com trade is on record"),
    ("Paul Rotter", r"\bPaul Rotter\b", "B", "Bund futures", "known scalper; own figures"),
    ("Victor Sperandeo", r"\bVictor Sperandeo\b|\bTrader Vic\b", "B", "futures", "Schwager interview"),
    ("Jack Schwager", r"\bJack Schwager\b", "B", "interviewer", "interviewer of Market Wizards"),
    ("Mike Bellafiore", r"\bMike Bellafiore\b|\bSMB Capital\b", "C", "prop firm", "owns SMB Capital; also sells training"),
    ("Tarek Elmarhri", r"\bElmarhri\b|\bEl Marhri\b|\bKrechendo\b", "C", "futures order flow", "owns Krechendo Trading; promotes a prop-firm challenge"),
    # market makers and high-frequency firms (filings)
    ("Doug Cifu", r"\bDoug(las)? Cifu\b|\bVirtu Financial\b", "A", "market maker", "Virtu's public filings"),
    ("Vincent Viola", r"\bVinnie Viola\b|\bVincent Viola\b", "A", "market maker", "Virtu's founder"),
    ("Don Wilson", r"\bDon Wilson\b|\bDRW\b", "B", "prop firm", "DRW's founder"),
    ("Peng Zhao", r"\bPeng Zhao\b|\bCitadel Securities\b", "A", "market maker", "Citadel Securities' bond filings"),
    ("Alex Gerko", r"\bAlex(ander)? Gerko\b|\bXTX Markets\b|\bZar Amrolia\b", "A", "market maker", "XTX's UK filed accounts"),
    ("Jane Street", r"\bJane Street\b|\bSignals and Threads\b", "A", "market maker", "bond filings and the 2025 SEBI order"),
    ("Optiver", r"\bOptiver\b", "B", "market maker", "private"),
    ("Hudson River Trading", r"\bHudson River Trading\b|\bHRT\b", "B", "market maker", "private"),
    ("Jump Trading", r"\bJump Trading\b|\bJump Crypto\b|\bKanav Kariya\b", "A", "prop firm", "court records (Terra, SEC v. Tai Mo Shan)"),
    ("Two Sigma", r"\bTwo Sigma\b", "B", "quant fund", "private"),
    # crypto trading firms and traders
    ("Evgeny Gaevoy", r"\bEvgeny Gaevoy\b|\bWintermute\b", "B", "crypto market maker", "Wintermute's founder"),
    ("GSR", r"\bGSR\b|\bRich Rosenblum\b", "B", "crypto market maker", "private"),
    ("B2C2", r"\bB2C2\b|\bMax Boonen\b", "B", "crypto market maker", "private"),
    ("Cumberland", r"\bCumberland\b", "B", "crypto OTC", "DRW's crypto arm"),
    ("Sam Bankman-Fried", r"\bBankman-Fried\b|\bSBF\b|\bAlameda\b", "A", "crypto arbitrage", "trial testimony and records"),
    ("Caroline Ellison", r"\bCaroline Ellison\b", "A", "crypto arbitrage", "sworn testimony"),
    ("Sam Trabucco", r"\bSam Trabucco\b", "B", "crypto arbitrage", "ex-Alameda co-CEO"),
    ("Su Zhu", r"\bSu Zhu\b|\bThree Arrows\b|\b3AC\b", "B", "crypto fund", "3AC; the liquidators' reports"),
    ("Kyle Davies", r"\bKyle Davies\b", "B", "crypto fund", "3AC co-founder"),
    ("Arthur Hayes", r"\bArthur Hayes\b", "A", "crypto exchange", "BitMEX's founder (court record)"),
    ("Cobie", r"\bCobie\b|\bUpOnly\b", "B", "crypto trader", "public calls; Echo sold to Coinbase"),
    ("GCR", r"\bGCR\b|\bGigantic Rebirth\b", "B", "crypto trader", "public calls"),
    ("Hsaka", r"\bHsaka\b", "C", "crypto trader", "public calls"),
    ("Ansem", r"\bAnsem\b", "C", "crypto trader", "public calls"),
    ("Andrew Kang", r"\bAndrew Kang\b|\bMechanism Capital\b", "B", "crypto fund", "Mechanism Capital"),
    ("Tetranode", r"\bTetranode\b", "B", "crypto DeFi", "on-chain wallet is public"),
    ("Joe McCann", r"\bJoe McCann\b|\bAsymmetric\b", "B", "crypto fund", "Asymmetric"),
    ("Dan Matuszewski", r"\bMatuszewski\b|\bCMS Holdings\b", "B", "crypto fund", "CMS Holdings"),
    ("Jordi Alexander", r"\bJordi Alexander\b|\bSelini\b", "B", "crypto trading firm", "Selini Capital"),
    ("Hasu", r"\bHasu\b", "B", "crypto research", "Flashbots, Lido"),
    ("Kyle Samani", r"\bKyle Samani\b|\bMulticoin\b", "B", "crypto fund", "Multicoin Capital"),
    ("Mike Novogratz", r"\bNovogratz\b|\bGalaxy Digital\b", "A", "crypto firm", "Galaxy's public filings"),
    ("James Wynn", r"\bJames Wynn\b", "C", "crypto perps", "public Hyperliquid positions"),
]

# phrases people use when they say where the money came from; (regex, weight)
CUES = [
    (r"\b(made|make|making|makes) (most|all|the bulk|a lot|almost all) of (our|my|their|his|the) money\b", 4),
    (r"\bhow (we|i|they|he) (made|make|makes) (our|my|their|his)? ?money\b", 4),
    (r"\bwhere (the|our|my) (money|p&l|pnl|profits?|returns?) (came|comes|come) from\b", 4),
    (r"\b(our|my|the|their|his) edge (was|is|came|comes)\b", 3),
    (r"\b(the|our|my|his|their) (best|biggest) (trade|month|year|day)\b", 2),
    (r"\bthe trade (was|is)\b", 2),
    (r"\bwe were (the only|basically the only|one of the few)\b", 3),
    (r"\b(nobody|no one) (else )?(was|is|were) (doing|looking|trading)\b", 3),
    (r"\bfree money\b", 3),
    (r"\b(arbitrage|arb|arbs)\b", 2),
    (r"\binefficien(t|cy|cies)\b", 2),
    (r"\b(who is|who's|who was) on the other side\b|\bthe other side of (the|that|our|my) trade\b", 3),
    (r"\bforced (sellers?|buyers?|selling|buying|liquidations?)\b", 3),
    (r"\bliquidat(ion|ions|ed)\b", 1),
    (r"\brebates?\b", 2),
    (r"\b(market making|market maker|liquidity provi(der|sion|ding))\b", 1),
    (r"\bpayment for order flow\b", 2),
    (r"\b(index )?rebalanc(e|es|ing)\b", 2),
    (r"\b(funding rate|basis trade|cash and carry|carry trade)\b", 2),
    (r"\bkimchi\b|\bpremium (in|on) (korea|japan)\b", 3),
    (r"\b(expiry|expiration|opex|options? expir)\w*\b", 1),
    (r"\b(new )?listings?\b", 1),
    (r"\b(retail|dumb money|tourists)\b", 1),
    (r"\bstructural\b", 1),
    (r"\b(i|we) (would|used to) (buy|sell|short|go long|fade)\b", 3),
    (r"\bthe (reason|secret) (it|this|that) works\b|\bwhy (it|this) works\b", 3),
    (r"\b(to be honest|honestly|frankly), (we|i)\b", 1),
    (r"\b(scalp|scalping|order flow|order book|tape reading)\b", 1),
    # French
    (r"\b(on|je|nous) (gagn\w+) (de l'argent|notre vie|ma vie|beaucoup)\b", 4),
    (r"\b(mon|notre) (edge|avantage)\b", 3),
    (r"\bcontrepartie\b", 2),
    (r"\bcarnet d'ordres?\b|\bflux d'ordres\b|\bgros intervenants\b", 2),
    (r"\b(je|on|nous) (prends|prend|achète|achetons|vends|vendons) (quand|lorsque|au moment)\b", 3),
]
CUE_RX = [(re.compile(rx, re.I), w) for rx, w in CUES]
NUM_RX = re.compile(r"\d[\d,.]*\s?(%|percent|bps?|basis points|million|billion|k\b|x\b)|\$\s?\d", re.I)
FEEDS_FR = {"so_what_fr"}                          # French feeds: the multilingual whisper model


def match(episodes=None):
    df = pd.read_csv(episodes or OUT / "episodes.csv").fillna({"title": "", "summary": "", "transcript": "",
                                                                "transcript_type": "", "audio": ""})
    rows = []
    for name, rx, tier, domain, why in ROSTER:
        r = re.compile(rx,re.I)
        in_title = df.title.map(lambda s: bool(r.search(s)))
        in_summary = df.summary.map(lambda s: bool(r.search(s))) & ~in_title
        for where, m in (("title", in_title), ("summary", in_summary)):
            for e in df[m].itertuples():
                rows.append({"person": name, "tier": tier, "domain": domain, "where": where, "key": e.key,
                             "feed": e.feed, "title": e.title, "pub_utc": e.pub_utc, "duration_s": e.duration_s,
                             "transcript": e.transcript, "transcript_type": e.transcript_type, "audio": e.audio})
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["tier", "person", "where", "pub_utc"], ascending=[True, True, False, False])
    return out


def guest(title, rx):
    """True when a title reads as the person speaking ("ft. X", "with X", "X on ...", "X: ...") rather than as a story
    about them."""
    if re.search(r"\b(untold story|what happened to|who was|biography of|remembering)\b",title,re.I):return False
    return bool(re.search(rf"(^|ft\.?|feat\.?|\bwith|w/|interview(ing)?|chats? with)\s*(?:{rx})|(?:{rx})\s*(on|–|-|:|,|"
                          rf"discusses|talks|explains|\|)", title,re.I))


def priority(t):
    """Order of work: feed transcripts first; then round-robin over people, so each person's best episode comes
    before anyone's second (a guest appearance before a story about them, tier A first, newest first)."""
    rx = {n: r for n, r, *_ in ROSTER}
    t = t.assign(_t=t.tier.map({"A": 0, "B": 1, "C": 2}), _w=(t["where"] != "title").astype(int),
                 _x=(t.transcript.fillna("") == "").astype(int),
                 _g=[0 if guest(str(ti), rx.get(p, "$^")) else 1 for ti, p in zip(t.title, t.person)])
    t = t.sort_values(["_g", "_w", "pub_utc"], ascending=[True, True, False])
    t = t.assign(_n=t.groupby("person").cumcount())
    return t.sort_values(["_x", "_n", "_t", "_g", "_w"])


def fetch(talks, whisper_python=None, tmp=None, max_hours=0.0, people=None, get=dp.get, run=subprocess.run):
    t=talks
    if people:
        t = t[t.person.str.contains(people, case=False, regex=True)]
    t = priority(t.drop_duplicates("key"))
    SUBS.mkdir(parents=True, exist_ok=True)
    spent, done = 0.0, []
    for r in t.itertuples():
        out = SUBS / f"pod_{r.key}.txt"
        if out.exists():
            continue
        try:
            if r.transcript:
                out.write_text(dp.transcript_text(get(r.transcript), r.transcript_type))
                how = "feed transcript"
            elif whisper_python and r.audio and r.where == "title":
                hours = (r.duration_s or 3600) / 3600
                if spent + hours > max_hours:
                    continue
                tmpd = Path(tmp)
                tmpd.mkdir(parents=True, exist_ok=True)
                audio = tmpd / f"{r.key}.audio"
                audio.write_bytes(get(r.audio, timeout=900))
                env = {"WHISPER_MODEL": "small"} if r.feed in FEEDS_FR else {}
                run([whisper_python, str(ROOT / "scripts" / "transcribe_audio.py"), str(audio), str(out)],
                    check=True, timeout=6 * 3600, env={**os.environ, **env})
                audio.unlink(missing_ok=True)
                spent += hours
                how = f"whisper ({spent:.1f} h of {max_hours} h)"
            else:
                continue
        except Exception as e:  # noqa: BLE001 - one bad episode does not stop the rest
            log(f"{r.person} {r.key}: failed ({type(e).__name__}: {e})")
            continue
        done.append(r.key)
        log(f"{r.person} [{r.tier}] {how}: {len(out.read_text().split())} words | {r.title[:70]}")
    return done


def windows(text, width=WINDOW):
    """Scored windows around cue hits; overlapping windows merge into the higher-scoring one."""
    words = text.split()
    joined = " ".join(words)
    starts, pos, hits = [], 0, []
    for w in words:                                 # character offset of each word in `joined`
        starts.append(pos)
        pos += len(w) + 1
    for rx, w in CUE_RX:
        for m in rx.finditer(joined):
            hits.append((bisect.bisect_right(starts, m.start()) - 1, w, m.group(0)))
    hits.sort()
    out = []
    for i, w, cue in hits:
        lo, hi = max(0, i - width), min(len(words), i + width)
        if out and lo <= out[-1]["hi"]:
            out[-1]["hi"] = max(out[-1]["hi"], hi)
            out[-1]["cues"].append(cue)
            out[-1]["score"] += w
            continue
        out.append({"lo": lo, "hi": hi, "cues": [cue], "score": w})
    for o in out:
        seg = " ".join(words[o["lo"]:o["hi"]])
        first = len(re.findall(r"\b(we|i|our|my|nous|je|on)\b", seg, re.I)) / max(1, o["hi"] - o["lo"])
        o["score"] += min(3, len(NUM_RX.findall(seg))) + (2 if first > 0.04 else 0)
        o["text"] = seg
    return out


def cues(talks, per_person=12):
    keys = talks.drop_duplicates("key")
    rows = []
    for r in keys.itertuples():
        p = SUBS / f"pod_{r.key}.txt"
        if not p.exists():
            continue
        for w in windows(p.read_text()):
            rows.append({"person": r.person, "tier": r.tier, "where": r.where, "key": r.key, "feed": r.feed,
                         "title": r.title, "pub_utc": r.pub_utc, "score": w["score"], "cues": sorted(set(w["cues"])),
                         "text": w["text"]})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values(["tier", "person", "score"], ascending=[True, True, False])
    return df.groupby("person", sort=False).head(per_person)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["match", "fetch", "cues"])
    ap.add_argument("--whisper-python", default=None)
    ap.add_argument("--tmp", default=None)
    ap.add_argument("--max-hours", type=float, default=0.0, help="fetch: hours of audio to transcribe at most")
    ap.add_argument("--people", default=None, help="fetch: only people matching this regex")
    ap.add_argument("--per-person", type=int, default=12)
    a = ap.parse_args(argv)
    talks_path = OUT / "talks.csv"
    if a.cmd == "match":
        t = match()
        t.to_csv(talks_path, index=False)
        g = t.groupby(["tier", "person"]).agg(episodes=("key", "nunique"), in_title=("where", lambda s: (s == "title").sum()),
                                              transcripts=("transcript", lambda s: (s.fillna("") != "").sum()))
        print(g.to_string())
        log(f"{t.key.nunique()} episodes for {t.person.nunique()} people -> {talks_path.relative_to(ROOT)}")
    elif a.cmd == "fetch":
        fetch(pd.read_csv(talks_path).fillna({"transcript": "", "transcript_type": "", "audio": ""}),
              a.whisper_python, a.tmp, a.max_hours, a.people)
    else:
        df = cues(pd.read_csv(talks_path), a.per_person)
        with open(OUT / "talk_cues.jsonl", "w") as f:
            for r in df.to_dict("records"):
                f.write(json.dumps(r) + "\n")
        with open(OUT / "talk_cues.md", "w") as f:
            for r in df.itertuples():
                f.write(f"## {r.person} [{r.tier}] {r.score} | {r.feed} {r.pub_utc[:10]} | {r.title}\n"
                        f"cues: {', '.join(r.cues)}\n\n{r.text}\n\n")
        log(f"{len(df)} windows for {df.person.nunique() if len(df) else 0} people -> data/videos/talk_cues.md")


if __name__ == "__main__":
    main()
