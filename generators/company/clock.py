"""The world clock. One instant per minute: t = 0 is the creation of the company (Monday, 1 June 2026, midnight); each step of
the world advances t and makes minute t happen. The clock never runs by itself: it only advances when the world steps.

There are two times. Real time (t) is the time of the interface clock: day(), minute_of_day(), day_of_week(). The calendar is the
time the company processes live by: the hour people arrive, the weekday on which versions are released, the end of the month for
sales, the time of the server's scheduled jobs. In the normal company the two coincide. In the "embaralhado" (shuffled) null variant
the calendar is drawn in blocks of variable length: each block gets a random hour, weekday and day of the month, and inside the
block the calendar runs minute by minute; durations and cause-and-effect delays stay in real minutes. Every hourly, daily and
monthly cycle disappears and the rest of the company stays the same."""
import datetime
import time

from .catalog import rng_for, MINUTES_PER_DAY

START_DATE = datetime.date(2026, 6, 1)       # a Monday
REFERENCE_DAYS = 364                    # the year from which the shuffled calendar draws its dates


class Calendar:
    """What the wall calendar and the wall clock tell the people working in the company in that minute."""
    __slots__ = ("absolute", "date", "minute", "weekday", "day_of_month", "days_in_month", "month", "workday", "sprint", "sprint_day")

    def set_time(self, absolute):
        self.absolute = absolute
        date = absolute // MINUTES_PER_DAY
        self.minute = absolute % MINUTES_PER_DAY
        if getattr(self, "date", None) != date:
            self.date = date
            d = START_DATE + datetime.timedelta(days=date)
            self.weekday = date % 7
            self.day_of_month = d.day
            next_month = (d.replace(day=28) + datetime.timedelta(days=4))
            self.days_in_month = (next_month - datetime.timedelta(days=next_month.day)).day
            self.month = (d.year - START_DATE.year) * 12 + d.month - START_DATE.month
            self.workday = self.weekday < 5
            self.sprint = date // 14             # two-week sprints start on Mondays
            self.sprint_day = date % 14
            return True
        return False

    def hour(self):
        return self.minute / 60.0

    def end_of_month(self):
        return self.day_of_month > self.days_in_month - 6

    def text(self):
        return f"dia {self.date}, {self.minute // 60:02d}h{self.minute % 60:02d}"


class Clock:
    def __init__(self, seed, shuffled=False, real_time=False):
        self.t = 0
        self.shuffled = shuffled
        self.real_time = real_time
        self.rng = rng_for(seed, "calendario embaralhado")
        self.cal = Calendar()
        self.cal.set_time(0)
        self.cal.date = None                  # the first step enters day 0 as a new date
        self.block = None                     # (real start, real end, start in the calendar)
        self.blocks = []                      # for the ground truth: the drawn blocks
        self._wall = None

    # ---------- interface clock ----------
    def day(self):
        return self.t // MINUTES_PER_DAY

    def minute_of_day(self):
        return self.t % MINUTES_PER_DAY

    def day_of_week(self):
        return self.day() % 7

    # ---------- one minute ----------
    def advance(self):
        """Advance the clock one minute; return True when the calendar enters a new date."""
        self.t += 1
        if not self.shuffled:
            return self.cal.set_time(self.t)
        if self.block is None or self.t >= self.block[1]:
            duration = self.rng.randint(25, 240)
            cal_start = self.rng.randrange(0, REFERENCE_DAYS * MINUTES_PER_DAY)
            self.block = (self.t, self.t + duration, cal_start)
            d = cal_start // MINUTES_PER_DAY
            date = START_DATE + datetime.timedelta(days=d)
            m = cal_start % MINUTES_PER_DAY
            self.blocks.append({"inicio": self.t, "fim": self.t + duration, "hora": f"{m // 60:02d}:{m % 60:02d}",
                                "dia_da_semana": d % 7, "dia_do_mes": date.day})
        return self.cal.set_time(self.block[2] + (self.t - self.block[0]))

    def wait_wall_clock(self):
        """In real-time mode, the step only ends when the corresponding wall-clock minute arrives. In simulation it never sleeps."""
        if not self.real_time:
            return
        now = time.monotonic()
        if self._wall is None:
            self._wall = now - 60.0 * self.t
        target = self._wall + 60.0 * self.t
        if target > now:
            time.sleep(target - now)

    def __getstate__(self):
        d = dict(self.__dict__)
        d["_wall"] = None
        return d
