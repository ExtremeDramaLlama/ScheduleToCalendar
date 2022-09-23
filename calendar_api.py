import datetime
import os.path
from typing import Iterable

import pendulum

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# singleton for credentials
creds = None

# set up week start and end (it defaults to starting on Monday)
pendulum.week_starts_at(pendulum.SUNDAY)
pendulum.week_ends_at(pendulum.SATURDAY)

CRISPIN_TUTOR_CALENDAR = (
    "b3bfc274a6acff119678202150dbd43b2fb2"
    "d7653c2885de7c78bdb75c81bda6@group.calendar.google.com"
)


class SimpleEvent:
    def __init__(
        self,
        summary: str,
        start: pendulum.DateTime,
        end: pendulum.DateTime,
        timezone="America/New_York",
    ):
        self.summary = summary
        self.start = start
        self.end = end
        self.timezone = timezone

    def __str__(self):
        return f"{self.summary}\n\tstart: {self.start}\n\tend: {self.end}"


def connect_oath():
    """
    Login via Oath and get credentials. The tokens.json file contains a refresh token,
    which (to the best of my knowledge) should last forever (or until access is revoked
    in the security settings of my account).
    """
    _creds = None
    # The file token.json stores the user's access and refresh tokens,
    # and is created automatically when the authorization flow completes
    # for the first time.
    if os.path.exists("token.json"):
        _creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not _creds or not _creds.valid:
        if _creds and _creds.expired and _creds.refresh_token:
            _creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "secrets/client_secrets.json", SCOPES
            )
            _creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(_creds.to_json())

    return _creds


def get_creds():
    global creds

    if creds:
        return creds

    creds = connect_oath()
    return creds


def add_events(events: Iterable[SimpleEvent]):
    for event in events:
        result = None
        try:
            service = build("calendar", "v3", credentials=get_creds())

            result = (
                service.events()
                .insert(
                    calendarId=CRISPIN_TUTOR_CALENDAR,
                    body={
                        "summary": event.summary,
                        "start": {
                            "dateTime": event.start.isoformat(),
                            "timeZone": event.timezone,
                        },
                        "end": {
                            "dateTime": event.end.isoformat(),
                            "timeZone": event.timezone,
                        },
                    },
                )
                .execute()
            )
        except HttpError as error:
            print(f"error while adding event: {error}")
            print(f"result: {result}")
            print(f"Event: {event}")
            raise


def get_events_for_week(date: pendulum.DateTime):
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """

    try:
        service = build("calendar", "v3", credentials=get_creds())

        # Call the Calendar API
        print("Getting the upcoming 10 events")
        events_result = (
            service.events()
            .list(
                calendarId=CRISPIN_TUTOR_CALENDAR,
                timeMin=date.start_of("week"),
                timeMax=date.end_of("week"),
                maxResults=20,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(start, event["summary"])

    except HttpError as error:
        print("An error occurred: %s" % error)


if __name__ == "__main__":
    # print("Logging in and writing token.json")
    get_events_for_week(pendulum.today("America/New_York"))
