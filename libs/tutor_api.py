import re
import json
from collections import abc
from typing import Iterator
from dataclasses import dataclass

from bs4 import BeautifulSoup
import mechanize
import pendulum
from pendulum import DateTime

from libs.calendar_api import SimpleEvent


# logger = logging.getLogger("mechanize")
# logger.addHandler(logging.StreamHandler(sys.stdout))
# logger.setLevel(logging.DEBUG)

with open("secrets/login_credentials.json", "r") as f:
    credentials = json.load(f)


DAYS_OF_WEEK = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]

br = mechanize.Browser()
br.set_handle_robots(False)

# Sets up week start and end (it defaults to starting on Monday).
# Fun fact: this doesn't affect .day_of_week and .weekday(), because
# those are delegated to the stdlib DateTime which doesn't know about
# pendulum's starting/ending days. Do I need them for anything?
# I don't know!
pendulum.week_starts_at(pendulum.SUNDAY)
pendulum.week_ends_at(pendulum.SATURDAY)


class Schedule(abc.Mapping):
    def __init__(self, html):
        html = BeautifulSoup(html, features="html5lib")
        self.hours_scheduled = int(html.find(id="lblScheduledHours").text)
        self.week = self.parse_week(html)
        self._schedule: dict[str, dict[int, str]] = self.parse_schedule(html)

    @staticmethod
    def parse_week(html: BeautifulSoup) -> DateTime:
        """
        Extract the week from the schedule page and parse it into a
        DateTime.
        """
        script = str(html.form.find_all("script")[-1].string)
        m = re.search(r"WEEK OF (\d\d/\d\d/\d\d\d\d) -", script)
        return pendulum.from_format(m.group(1), "MM/DD/YYYY", tz="America/New_York")

    @staticmethod
    def parse_schedule(html: BeautifulSoup) -> dict[str, dict[int, str]]:
        script = str(html.form.find_all("script")[-1].string)
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
        schedule: dict[str, dict[int, str]] = {day: dict() for day in DAYS_OF_WEEK}
        for index, status in extracted_cells:
            if status:
                # Note that the javascript cells don't match to the table
                # cells. This is only the selectable portion of the table,
                # so only 7 wide.
                hour = index // 7
                day = index % 7
                schedule[DAYS_OF_WEEK[day]][hour] = status
        return schedule

    def to_simple_events(self):
        @dataclass
        class Event:
            """Stupid simple event to keep the logic simple"""

            start: int
            end: int

        # Collapse nearby hours into one Event
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

    def ascii_display(self) -> str:
        lines = [
            f"Week of {self.week.format('MM/DD/YYYY')}",
            "   " + " ".join(DAYS_OF_WEEK),
        ]

        for hour in range(24):
            line = str(hour).rjust(2) + " "
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


def build_schedule_hour_url(timeslot: DateTime, unset=False):
    """
    Build the URL that will actually schedule the given 1-hour timeslot.

    type: "Set"|"Remove"
    Week: "mm/dd/yyyy"
    weekDay: int, 1-7
    hour: "9PM"
    """

    # The week actually has to be the start of the week, just like how
    # the schedule displays it. I haven't tested it yet, but depending
    # on the backend, it may be possible to use the timeslot date
    # without modification, and set weekday to 1.
    week = timeslot.subtract(days=timeslot.day_of_week)
    week = week.format("MM/DD/YYYY")
    weekday = timeslot.day_of_week + 1
    hour = timeslot.format("hA")
    type_ = "Remove" if unset else "Set"

    return (
        "https://prv.tutor.com/nGEN/Tools/ScheduleManager_v2/"
        f"SchedulerWorker.aspx?Type={type_}"
        f"&Week={week}"
        f"&WeekDay={weekday}"
        f"&Hour={hour}"
    )


def build_login_url(program_guid, user_guid):
    """
    Build URL for login page. The program/user GUIDs are both unique
    to users (I assume, haven't checked) and the page won't load without them.
    We could avoid needing them if we logged in from the main tutor.com page
    and then navigated to the schedule.
    """
    return (
        f"https://prv.tutor.com/"
        "nGEN/Tools/ScheduleManager_v2/setContactID.aspx"
        f"?ProgramGUID={program_guid}&UserGUID={user_guid}"
    )


def build_week_url(week: str):
    """
    Builds the URL for the schedule page for a given week. Week is in the
    form of `mm/dd/yyyy`.
    """
    return (
        f"https://prv.tutor.com/nGEN/Tools/"
        "ScheduleManager_v2/default.aspx?"
        f"SelectedDate={week}&DaysToAdd=0"
    )


# TODO: accept a single precise DateTime, or a
#       DateTime that's within the week sometime
def schedule_hour(week: DateTime, day: int, hour: int, unset=False) -> bool:
    """
    `week` is the start of the week.
    `day` is 0-6 -- sunday is zero.
    `hour` is 0-23
    """
    slot = week.add(days=day, hours=hour)
    url = build_schedule_hour_url(slot, unset=unset)
    response = mechanize.Request(url, method="POST")

    response = br.open(response).get_data()
    if response == b"ScheduleSelectedComplete(1);":
        return True
    elif response == b"ScheduleSelectedComplete(0);":
        return False
    else:
        raise Exception(f"Unforeseen response: {response}")


def login_and_get_html() -> str:
    """
    Logs in and returns the HTML form the schedule page, which will
    be for the current week.

    Calling this twice will crash things, because the login page will be
    skipped, and mechanize won't be able to find the login form.
    """
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


def get_html_for_week(week: str | DateTime) -> str:
    """
    Loads the schedule for the given week and returns the HTML. The user
    MUST be logged in already.
    """
    if type(week) == DateTime:
        week = week.format("MM/DD/YYYY")
    # TODO: make the login a singleton type deal
    url = build_week_url(week)
    response = br.open(url)
    if response.code != 200:
        raise Exception(f"Opening week URL gave error code: {response.code} ")
    return str(response.get_data())


def main():
    # week = DateTime.now().add(weeks=1)
    # add_week_to_calendar(week)
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
