import sys, logging
import re
import json
from collections import abc
from typing import TypedDict, Literal, Iterator
from dataclasses import dataclass

from bs4 import BeautifulSoup
import mechanize
import pendulum
from pendulum import DateTime

import calendar_api
from calendar_api import SimpleEvent


# logger = logging.getLogger("mechanize")
# logger.addHandler(logging.StreamHandler(sys.stdout))
# logger.setLevel(logging.DEBUG)

with open("secrets/login_credentials.json", "r") as f:
    credentials = json.load(f)


DAYS_OF_WEEK = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]

br = mechanize.Browser()


class Schedule(abc.Mapping):
    def __init__(self, week: DateTime):
        self.week = week
        self._schedule: dict[str, dict[int, str]] = {
            day: dict() for day in DAYS_OF_WEEK
        }

    def to_simple_events(self):
        @dataclass
        class Event:
            """Stupid simple event to keep the logic simple"""

            start: int
            end: int

        # Collapse nearby hours into one
        def join_times(times: list[int]) -> list[Event]:
            if not times:
                return []
            t1 = times.pop(0)
            collapsed = [Event(t1, t1 + 1)]
            current = 0
            for t2 in times:
                t1 = collapsed[current]
                if t1.end == t2:
                    t1.end = t2 + 1
                else:
                    collapsed.append(Event(t2, t2 + 1))
                    current += 1
            return collapsed

        simple_events: dict[str, list[SimpleEvent]] = {}
        for day, hours in self._schedule.items():
            # filter out the Available time slots
            hours = [h for h in hours.keys() if hours[h] == "Scheduled!"]
            # collapse the times
            events = join_times(hours)
            # translate the stupid-simple event into SimpleEvents using
            # DateTime objects
            day_index = DAYS_OF_WEEK.index(day)
            simple_events_list = []
            for event in events:
                simple = SimpleEvent(
                    "Tutoring",
                    start=self.week.add(days=day_index, hours=event.start),
                    end=self.week.add(days=day_index, hours=event.end),
                )
                simple_events_list.append(simple)
            simple_events[day] = simple_events_list

        return simple_events

    def pretty(self) -> str:
        lines = [
            f"Week of {self.week.format('MM/DD/YYYY')}",
            "   " + " ".join(DAYS_OF_WEEK),
        ]

        for hour in range(24):
            line = str(hour)
            for daily_schedule in self.values():
                if status := daily_schedule.get(hour):
                    line += f" {status[0]}  "
                else:
                    line += "    "
            lines.append(line)

        return "\n".join(lines)

    def values(self):
        return self._schedule.values()

    def __getitem__(self, k: str):
        if k not in DAYS_OF_WEEK:
            raise Exception(f"Expected day of week, got: {k}")
        return self._schedule[k]

    def __len__(self) -> int:
        return len(self._schedule)

    def __iter__(self) -> Iterator:
        return self._schedule.__iter__()


def build_schedule_hour_url(timeslot: DateTime, unset=True):
    """
    url = 'SchedulerWorker.aspx?Type=' + m_Type +
    '&Week=' + selectedWeekDate +
    '&WeekDay=' + weekDay +
    '&Hour=' + hour;

    m_Type: "Set"|"Remove"
    selectedWeekDate: "09/11/2022"
    weekDay: int, 1-7
    hour: "9PM"
    """
    week = timeslot.format("DD/MM/YYYY")


def build_login_url(program_guid, user_guid):
    return (
        f"https://prv.tutor.com/"
        "nGEN/Tools/ScheduleManager_v2/setContactID.aspx"
        f"?ProgramGUID={program_guid}&UserGUID={user_guid}"
    )


def build_week_url(week):
    """Week in the form of `09/25/2022`"""
    return (
        f"https://prv.tutor.com/nGEN/Tools/"
        "ScheduleManager_v2/default.aspx?"
        f"SelectedDate={week}&DaysToAdd=0"
    )


def parse_schedule(html, week) -> Schedule:
    s = BeautifulSoup(html, features="html5lib")
    script = str(s.form.find_all("script")[-1].string)
    # Use +? to perform non-greedy match
    cell_calls = re.findall("fillCell\(.+?\)", script)
    extracted_cells: list[tuple[int, str]] = []
    for cell in cell_calls:
        # Extract the cell index and status ("Available" or
        # "Scheduled!") We need 2 backslashes because the HTML contains
        # a single backslash, and the regex parser needs it to be
        # escaped. We're using a raw string so we don't have to use even
        # more backslashes to escape these backslashes.
        pattern = r"fillCell\(.+, \\'(.+)\\', \\'(.*)\\',.+\)"
        index, status = re.search(pattern, cell).groups()
        extracted_cells.append((int(index), status))

    # parse the cell indices into hour and day
    schedule = Schedule(week)
    for index, status in extracted_cells:
        if status:
            # Note that the javascript cells don't match to the table
            # cells. This is only the selectable portion of the table,
            # so only 7 wide.
            hour = index // 7
            day = index % 7
            schedule[DAYS_OF_WEEK[day]][hour] = status
    return schedule


def login_and_get_html() -> str:
    """Login and scrape all HTML from schedule page"""
    url = build_login_url(credentials["program_id"], credentials["user_id"])
    br.open(url)
    form = br.forms()[0]
    form["txtUserName"] = credentials["username"]
    form["txtPassword"] = credentials["password"]
    br.form = form
    response = br.submit()
    if response.code != 200:
        raise Exception(
            (
                "Something went wrong with form submission -- "
                "maybe the username or password was wrong?"
            )
        )
    return str(response.get_data())


def get_html_for_week(week: str) -> str:
    """Loads the schedule for the given week and returns the HTML.
    The user MUST be logged in already."""
    # TODO: make the login a singleton type deal
    url = build_week_url(week)
    print(url)
    response = br.open(url)
    if response.code != 200:
        raise Exception(f"Opening week URL gave error code: {response.code} ")
    return str(response.get_data())


def parse_week(html) -> DateTime:
    """Grab the week from the schedule, parse into DateTime"""
    s = BeautifulSoup(html, features="html5lib")
    script = str(s.form.find_all("script")[-1].string)
    m = re.search(r"WEEK OF (\d\d/\d\d/\d\d\d\d) -", script)
    return pendulum.from_format(m.group(1), "MM/DD/YYYY", tz="America/New_York")


def add_current_week_to_calendar():
    page_data = login_and_get_html()
    week = parse_week(page_data)
    schedule = parse_schedule(page_data, week)
    simple_events = schedule.to_simple_events()

    # merge the schedule lists for all days
    whole_week = []
    for day_sched in simple_events.values():
        whole_week.extend(day_sched)

    # first delete the existing events for that week
    calendar_api.delete_all_events(calendar_api.get_events_for_week(week))

    # add the new events
    calendar_api.add_events(whole_week)


def main():
    pass

    # page_data = get_html_for_week("09/18/2022")
    # with open("tmp/week2.html", "w") as f:
    #     f.write(page_data)
    # week = parse_week(page_data)
    # schedule = parse_schedule(page_data)
    # print(schedule)
    # print_schedule(week, schedule)


if __name__ == "__main__":
    main()
