from libs import tutor_api, calendar_api
import pendulum
from pendulum import DateTime
from datetime import datetime
import click


@click.command(help="Add the current week's schedule to your calendar.")
@click.option(
    "--next", is_flag=True, help="Adds next week's schedule to your calendar."
)
@click.option(
    "--week",
    default=None,
    type=click.DateTime(["%m/%d/%Y"]),
    help=(
        "Specify a date within the week of the schedule that you want to "
        "add to your calendar, matching the form MM/DD/YYYY. For example, "
        "03/23/2022, or 11/09/2023. If --next was provided, this option is ignored."
    ),
)
def add_week_command(next: bool, week: datetime | None):
    week_to_add = DateTime.now()
    if next:
        week_to_add = DateTime.now().add(weeks=1)
    elif week:
        # Convert built-in DateTime to Pendulum's DateTime
        week_to_add = pendulum.parse(week.isoformat())
    add_week_to_calendar(week_to_add)

    print("It worked! Probably!")


def add_week_to_calendar(week: DateTime):
    """
    For the current or specified week, put all scheduled tutoring times
    into your Google calendar.
    """
    page_data = tutor_api.login_and_get_html()
    if week:  # currently unneeded, need to improve backend
        page_data = tutor_api.get_html_for_week(week)

    schedule = tutor_api.Schedule(page_data)
    simple_events = schedule.to_simple_events()

    # merge the schedule lists for all days
    whole_week = []
    for day_sched in simple_events.values():
        whole_week.extend(day_sched)

    # first delete the existing events for that week
    calendar_api.delete_all_events(calendar_api.get_events_for_week(week))

    # add the new events
    calendar_api.add_events(whole_week)


if __name__ == "__main__":
    add_week_command()
