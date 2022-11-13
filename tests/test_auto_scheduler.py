import auto_scheduler
from libs import tutor_api


class MockResponse:
    @staticmethod
    def get_data(*args, **kwargs):
        return b"ScheduleSelectedComplete(1);"


def create_test_schedule():
    with open("tests/page_data/schedule.html") as f:
        html = f.read()

    # create blank schedule
    sched = tutor_api.Schedule(html)
    for day in list(sched.keys()):
        sched._schedule[day] = {hour: "Available" for hour in range(24)}
    return sched


def test_auto_scheduler(monkeypatch):
    def mock_open(*args, **kwargs):
        print(args[0].get_full_url())

        return MockResponse()

    monkeypatch.setattr(auto_scheduler.tutor_api.br, "open", mock_open)
    s = create_test_schedule()
    print(s.ascii_display())

    auto_scheduler.schedule_hours(s)
    print(s.ascii_display())
