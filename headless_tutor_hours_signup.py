import mechanize
import sys, logging
from bs4 import BeautifulSoup
import re

logger = logging.getLogger("mechanize")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)

CRISPIN_PROGRAM_ID = "B611858B-4D02-4AFE-8053-D082BBC1C58E"
CRISPIN_USER_ID = "6d7bdaa9-d440-4ec1-b0d0-0467546b880e"
CRITTER_USER_NAME = "Crispinstichart+tutorcom@gmail.com"
CRITTER_PASSWORD = "dUe5m.x*7r5cZQh"

DAYS_OF_WEEK = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]

br = mechanize.Browser()


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


def parse_schedule(html) -> dict:
    s = BeautifulSoup(html, features="html5lib")
    script = str(s.form.find_all("script")[-1].string)
    # Use +? to perform non-greedy match
    cell_calls = re.findall("fillCell\(.+?\)", script)
    extracted_cells: list[tuple[int, str]] = []
    for cell in cell_calls:
        # Extract the cell index and status ("Available" or "Scheduled!")
        # We need 2 backslashes because the HTML contains a single backslash,
        # and the regex parser needs it to be escaped. We're using a raw string
        # so we don't have to use even more backslashes to escape these backslashes.
        pattern = r"fillCell\(.+, \\'(.+)\\', \\'(.*)\\',.+\)"
        index, status = re.search(pattern, cell).groups()
        extracted_cells.append((int(index), status))

    # parse the cell indices into hour and day
    schedule = {day: dict() for day in DAYS_OF_WEEK}
    for index, status in extracted_cells:
        if status:
            # Note that the javascript cells don't match to the table cells. This
            # is only the selectable portion of the table, so only 7 wide.
            hour = index // 7
            day = index % 7
            schedule[DAYS_OF_WEEK[day]][hour] = status
    return schedule


def print_schedule(week: str, schedule: dict[str, dict[int, str]]) -> None:
    print(f"Week of {week}")
    print("   " + " ".join(DAYS_OF_WEEK))

    for hour in range(24):
        line = str(hour)
        for daily_schedule in schedule.values():
            if status := daily_schedule.get(hour):
                line += f" {status[0]}  "
            else:
                line += "    "
        print(line)


def parse_week(html):
    s = BeautifulSoup(html, features="html5lib")
    script = str(s.form.find_all("script")[-1].string)
    m = re.search(r"WEEK OF (\d\d/\d\d/\d\d\d\d) -", script)
    return m.group(1)


def login_and_get_html() -> str:
    url = build_login_url(CRISPIN_PROGRAM_ID, CRISPIN_USER_ID)
    br.open(url)
    form = br.forms()[0]
    form["txtUserName"] = CRITTER_USER_NAME
    form["txtPassword"] = CRITTER_PASSWORD
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


def get_week_data(week: str) -> str:
    url = build_week_url(week)
    print(url)
    response = br.open(url)
    if response.code != 200:
        raise Exception(f"Opening week URL gave error code: {response.code} ")
    return str(response.get_data())


def main():
    page_data = login_and_get_html()
    # with open("tmp/schedule.html", "r") as f:
    #     page_data = str(f.read())

    week = parse_week(page_data)
    schedule = parse_schedule(page_data)
    print(schedule)
    print_schedule(week, schedule)

    page_data = get_week_data("09/18/2022")
    with open("tmp/week2.html", "w") as f:
        f.write(page_data)
    week = parse_week(page_data)
    schedule = parse_schedule(page_data)
    print(schedule)
    print_schedule(week, schedule)


if __name__ == "__main__":
    main()
