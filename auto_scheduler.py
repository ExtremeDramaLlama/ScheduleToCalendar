from libs import tutor_api
from pendulum import DateTime

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
WEEKENDS = ["TUE", "THU"]
START_TIME = 11
END_TIME = 21  # Don't schedule this hour or past it
MAX_PER_DAY = 8
MAX_PER_WEEK = 40


def main():
    _ = tutor_api.login_and_get_html()
    html = tutor_api.get_html_for_week(DateTime.now().add(weeks=1))

    schedule = tutor_api.Schedule(html)
    hours_before = schedule.hours_scheduled
    print(f"Currently scheduled for {hours_before} hours.")
    print("Commence auto scheduling!")
    schedule_hours(schedule)

    diff = schedule.hours_scheduled - hours_before
    print(
        f"Scheduled {diff} more hours hours, "
        f"for a total of {schedule.hours_scheduled}"
    )

    if schedule.hours_scheduled < MAX_PER_WEEK:
        print(
            f"Since you need {MAX_PER_WEEK - schedule.hours_scheduled} "
            f"to meet your desired work amount, I'm going to try to "
            f"schedule more than {MAX_PER_DAY} hours per day."
        )
        schedule_hours(schedule, ignore_daily_max=True)


def schedule_hours(schedule, ignore_daily_max=False):
    schedule_copy = {
        day: {hour: availability for hour, availability in hours.items()}
        for day, hours in schedule.items()
    }
    for day, hours in schedule_copy.items():
        if day in WEEKENDS:
            continue

        if schedule.hours_scheduled >= MAX_PER_WEEK:
            break

        day_of_week = tutor_api.DAYS_OF_WEEK.index(day)
        consecutive_hours = 0
        hours_for_day = list(schedule[day].values()).count("Scheduled!")
        for i in range(START_TIME, END_TIME):
            if consecutive_hours == 4:
                consecutive_hours = 0
                continue

            if hours_for_day >= MAX_PER_DAY and not ignore_daily_max:
                break

            if hours.get(i) == "Available":
                success = tutor_api.schedule_hour(schedule.week, day_of_week, i)
                if success:
                    schedule.hours_scheduled += 1
                    schedule[day][i] = "Scheduled!"
                    consecutive_hours += 1
                    hours_for_day += 1
                else:
                    consecutive_hours = 0
                    # someone got to it before us, so delete from schedule.
                    schedule[day].pop(i, None)
            elif hours.get(i) == "Scheduled!":
                consecutive_hours += 1
            else:
                consecutive_hours = 0


if __name__ == "__main__":
    main()
