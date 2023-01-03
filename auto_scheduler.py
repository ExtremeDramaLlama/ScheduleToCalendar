from libs import tutor_api
from pendulum import DateTime, Period
from threading import Thread, Barrier
import time

# get schedule for current week
# update hours_scheduled
# iterate through day by day
# don't add weekends
# Iterate hours starting with START_TIME
# Add hours one by one, only for available days
# Check return of API call for success
# increment hours if success
# if added 4 hours in row, skip hour
# # don't add more than 8 hours per day on first pass
# if hours less than 40, take second pass
# start after last scheduled hour
# don't violate previous rules
WEEKENDS = ["MON", "WED"]
START_TIME = 11
END_TIME = 24  # Don't schedule this hour or past it
MAX_PER_DAY = 8
MAX_PER_WEEK = 40


def main():
    _ = tutor_api.login_and_get_html()
    html = tutor_api.get_html_for_week(DateTime.now().add(weeks=1))

    schedule = tutor_api.Schedule(html)
    hours_before = schedule.hours_scheduled
    print(f"Currently scheduled for {hours_before} hours.")
    print("Commence auto scheduling!")

    hours_to_schedule = get_hours_to_schedule(schedule)
    successfully_scheduled = schedule_hours_in_threads(schedule.week, hours_to_schedule)

    schedule.hours_scheduled += len(successfully_scheduled)
    print(
        f"Scheduled {len(successfully_scheduled)} more hours, "
        f"for a total of {schedule.hours_scheduled}"
    )

    for day, hour in hours_to_schedule:
        day_name = tutor_api.DAYS_OF_WEEK[day]
        if (day, hour) in successfully_scheduled:
            schedule[day_name][hour] = "Scheduled!"
        else:
            del schedule[day_name][hour]

    # do it all again if we haven't hit our weekly maximum
    if schedule.hours_scheduled < MAX_PER_WEEK:
        print(
            f"Since you need {MAX_PER_WEEK - schedule.hours_scheduled} "
            f"to meet your desired work amount, I'm going to try to "
            f"schedule more than {MAX_PER_DAY} hours per day."
        )
        hours_to_schedule = get_hours_to_schedule(schedule, ignore_daily_max=True)
        successfully_scheduled = schedule_hours_in_threads(
            schedule.week, hours_to_schedule
        )

        schedule.hours_scheduled += len(successfully_scheduled)
        print(
            f"Scheduled {len(successfully_scheduled)} more hours, "
            f"for a total of {schedule.hours_scheduled}"
        )


def schedule_hours_in_threads(week: DateTime, hours_to_schedule: list[tuple[int, int]]):
    # The +1 is needed for this main thread
    barrier = Barrier(len(hours_to_schedule) + 1)
    successfully_scheduled: list[tuple[int, int]] = []
    # creating a list of threads first as a probably premature optimization
    threads = []
    for day, hour in hours_to_schedule:
        t = Thread(
            target=attempt_to_schedule_hour,
            args=(week, day, hour, successfully_scheduled, barrier),
        )
        threads.append(t)

    # now we wait until 11:00
    now = DateTime.now()
    # one second after eleven to provide some wiggle room for clock difference
    eleven = DateTime(now.year, now.month, now.day, 11, 0, 1)
    delta: Period = now.diff(eleven)
    if delta.in_seconds() > 0:
        print(f"Sleeping for {delta.in_seconds()} seconds")
        time.sleep(delta.in_seconds())

    # now we can launch those threads
    for thread in threads:
        thread.run()

    barrier.wait()

    return successfully_scheduled


def attempt_to_schedule_hour(
    week: DateTime, day: int, hour: int, successfully_scheduled: list, barrier: Barrier
):
    if tutor_api.schedule_hour(week, day, hour):
        successfully_scheduled.append((day, hour))

    barrier.wait()


# TODO: take into account hours before START_TIME when
#       initially setting consecutive_hours
def get_hours_to_schedule(schedule, ignore_daily_max=False) -> list[tuple[int, int]]:
    available_hours = []
    hours_scheduled = schedule.hours_scheduled
    schedule_copy = {
        day: {hour: availability for hour, availability in hours.items()}
        for day, hours in schedule.items()
    }
    for day, timeslots in schedule_copy.items():
        if day in WEEKENDS:
            continue

        if hours_scheduled >= MAX_PER_WEEK:
            break

        day_of_week = tutor_api.DAYS_OF_WEEK.index(day)
        consecutive_hours = 0
        hours_for_day = list(schedule[day].values()).count("Scheduled!")
        for hour in range(START_TIME, END_TIME):
            if consecutive_hours == 4:
                consecutive_hours = 0
                continue

            if hours_for_day >= MAX_PER_DAY and not ignore_daily_max:
                break

            if timeslots.get(hour) == "Available":
                available_hours.append((day_of_week, hour))
                # assume we can schedule it
                hours_scheduled += 1
                # schedule[day][hour] = "Scheduled!"
                consecutive_hours += 1
                hours_for_day += 1

                # success = tutor_api.schedule_hour(schedule.week, day_of_week, i)
                # if success:
                #     schedule.hours_scheduled += 1
                #     schedule[day][i] = "Scheduled!"
                #     consecutive_hours += 1
                #     hours_for_day += 1
                # else:
                #     consecutive_hours = 0
                #     # someone got to it before us, so delete from schedule.
                #     schedule[day].pop(i, None)
            elif timeslots.get(hour) == "Scheduled!":
                consecutive_hours += 1
            else:
                consecutive_hours = 0

    return available_hours


if __name__ == "__main__":
    main()
