"""Market clocks: where each decision time sits against the hours of other markets and scheduled events.

A panel row t is the hourly bar opening at t; its features are known at the bar's close, so the decision time is
tau = t + 1 h and the next bar's return covers [tau, tau + 1 h). Every clock below is a function of tau only, computed
in each exchange's own local time with daylight saving, so "the US open" stays the US open when clocks change
(a plain UTC hour moves by one hour twice a year). All clocks are integer codes, the same for every symbol.

us_clock      NYSE trading days: floor(hours from 09:30 New York), clipped to [-5, 8], stored as 0..13
              (code 4 = the next bar contains the open, 10 = it ends at the 16:00 close); 14 = no NYSE session.
eu_clock      London weekdays: floor(hours from 08:00 London), clipped to [-3, 9], as 0..12; 13 = weekend.
cme_clock     CME crypto futures week (Sun 18:00 to Fri 17:00 New York): 0 closed for the weekend, 1 first hour after
              the Sunday reopen, 2 hours 1-5 after it, 3 daily 17:00-18:00 maintenance break, 4 open,
              5 last 4 hours before the Friday close.
us_day        0 ordinary NYSE day, 1 Thursday (weekly jobless claims 08:30), 2 first Friday of the month (payrolls
              08:30), 3 FOMC statement day (14:00), 4 NYSE holiday on a weekday, 5 weekend.
expiry_clock  Monthly crypto options and CME futures expire on the last Friday of the month (Deribit at 08:00 UTC):
              0 expiry day before 08:00 UTC, 1 expiry day after, 2 one to three days before, 3 first three days of
              the month, 4 otherwise; +5 in March, June, September and December (quarterly expiry).
us_dst        1 while New York is on daylight-saving time.
"""
import numpy as np
import pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay, USMartinLutherKingJr,
                                    USMemorialDay, USPresidentsDay, USThanksgivingDay, nearest_workday,
                                    sunday_to_monday)

HOUR = 3_600_000

FOMC = """2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28 2026-12-09""".split()
# statement days of scheduled meetings, from federalreserve.gov/monetarypolicy/fomccalendars.htm (read 2026-10-18)


class NYSEHolidays(AbstractHolidayCalendar):
    rules = [Holiday("NewYear", month=1, day=1, observance=sunday_to_monday), USMartinLutherKingJr, USPresidentsDay,
             GoodFriday, USMemorialDay,
             Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
             Holiday("Independence", month=7, day=4, observance=nearest_workday), USLaborDay, USThanksgivingDay,
             Holiday("Christmas", month=12, day=25, observance=nearest_workday)]


def _local(tau_ms, tz):
    return pd.to_datetime(tau_ms, unit="ms", utc=True).tz_convert(tz)


def _hours(local):
    return np.asarray(local.hour + local.minute / 60.0)


def _nyse_open_day(ny):
    days = ny.normalize().tz_localize(None)
    hol = NYSEHolidays().holidays(days.min(), days.max())
    return np.asarray((ny.weekday < 5) & ~days.isin(hol)), np.asarray(days.isin(hol) & (ny.weekday < 5))


def us_clock(tau):
    ny = _local(tau, "America/New_York")
    trading, _ = _nyse_open_day(ny)
    c = np.clip(np.floor(_hours(ny) - 9.5), -5, 8) + 5
    return np.where(trading, c, 14).astype(np.float32)


def eu_clock(tau):
    ld = _local(tau, "Europe/London")
    c = np.clip(np.floor(_hours(ld) - 8.0), -3, 9) + 3
    return np.where(np.asarray(ld.weekday) < 5, c, 13).astype(np.float32)


def cme_clock(tau):
    ny = _local(tau, "America/New_York")
    wd, h = np.asarray(ny.weekday), _hours(ny)
    week_h = wd * 24 + h                                   # hours since Monday 00:00 New York
    since_open = (week_h - (6 * 24 + 18)) % (7 * 24)       # hours since Sunday 18:00
    closed = since_open >= (4 * 24 + 23)                   # Friday 17:00 to Sunday 18:00
    brk = (h >= 17) & (h < 18) & (wd < 4)
    last4 = (wd == 4) & (h >= 13) & (h < 17)
    c = np.select([closed, since_open < 1, since_open < 6, brk, last4], [0, 1, 2, 3, 5], 4)
    return c.astype(np.float32)


def us_day(tau):
    ny = _local(tau, "America/New_York")
    trading, holiday = _nyse_open_day(ny)
    wd, dom = np.asarray(ny.weekday), np.asarray(ny.day)
    days = ny.normalize().tz_localize(None)
    fomc = np.asarray(days.isin(pd.to_datetime(FOMC)))
    c = np.select([wd >= 5, holiday, fomc, (wd == 4) & (dom <= 7), wd == 3], [5, 4, 3, 2, 1], 0)
    return c.astype(np.float32)


def expiry_clock(tau):
    ts = _local(tau, "UTC")
    day = ts.normalize().tz_localize(None)
    month_end = day + pd.offsets.MonthEnd(0)
    last_fri = month_end - pd.to_timedelta((month_end.weekday - 4) % 7, unit="D")
    to_exp = np.asarray((last_fri - day).days)
    hour = np.asarray(ts.hour)
    c = np.select([(to_exp == 0) & (hour < 8), to_exp == 0, (to_exp >= 1) & (to_exp <= 3), np.asarray(ts.day) <= 3],
                  [0, 1, 2, 3], 4)
    quarterly = np.isin(np.asarray(ts.month), (3, 6, 9, 12))
    return (c + 5 * quarterly).astype(np.float32)


def us_dst(tau):
    ny = _local(tau, "America/New_York")
    off = np.asarray(ny.tz_localize(None) - ny.tz_convert("UTC").tz_localize(None)) / np.timedelta64(1, "h")
    return (off == -4).astype(np.float32)


CLOCKS = {"us_clock": (us_clock, 15), "eu_clock": (eu_clock, 14), "cme_clock": (cme_clock, 6), "us_day": (us_day, 6),
          "expiry_clock": (expiry_clock, 10), "us_dst": (us_dst, 2)}


def decision_time(t):
    """Decision time of each panel row: the close of the bar that opens at t."""
    return np.asarray(t, np.int64) + HOUR


def codes(t, name):
    """[T] float32 code of one clock for panel open times t."""
    return CLOCKS[name][0](decision_time(t))
