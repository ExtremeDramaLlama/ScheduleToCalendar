import os.path
from typing import Iterable
import json

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

with open("secrets/login_credentials.json", "r") as f:
    credentials = json.load(f)


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
    TOKENS_FILE = "secrets/token.json"
    SECRETS_FILE = "secrets/client_secrets.json"
    if os.path.exists(TOKENS_FILE):
        _creds = Credentials.from_authorized_user_file(TOKENS_FILE, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not _creds or not _creds.valid:
        if _creds and _creds.expired and _creds.refresh_token:
            _creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
            _creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKENS_FILE, "w") as token:
            token.write(_creds.to_json())

    return _creds


def get_creds():
    global creds

    if creds:
        return creds

    creds = connect_oath()
    return creds


def batch_callback(id_, _response, exception):
    if exception:
        print(f"Error with batch request, id={id_}")
        raise Exception(str(exception))

    # if response:
    #     print(response)


def add_events(events: Iterable[SimpleEvent]):
    service = build("calendar", "v3", credentials=get_creds())
    batch = service.new_batch_http_request(callback=batch_callback)
    # TODO: only batch 50 at a time, which is the limit. I don't thing
    #       that the library automatically splits them up.
    for event in events:
        batch.add(
            service.events().insert(
                calendarId=credentials["calendar_id"],
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
        )
    batch.execute()


def delete_all_events(events: list[dict]):
    service = build("calendar", "v3", credentials=get_creds())
    batch = service.new_batch_http_request(callback=batch_callback)
    # TODO: only batch 50 at a time, which is the limit. I don't thing
    #       that the library automatically splits them up.
    for event in events:
        batch.add(
            service.events().delete(
                calendarId=credentials["calendar_id"], eventId=event["id"]
            )
        )
    batch.execute()


def get_events_for_week(date: pendulum.DateTime) -> list:
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    events = []

    try:
        service = build("calendar", "v3", credentials=get_creds())
        # Call the Calendar API
        print("Getting the upcoming 10 events")
        request = service.events().list(
            calendarId=credentials["calendar_id"],
            timeMin=date.start_of("week"),
            timeMax=date.end_of("week"),
            singleEvents=True,
            orderBy="startTime",
        )

        # pagination
        while request is not None:
            result = request.execute()
            events.extend(result.get("items", []))
            request = service.events().list_next(request, result)

    except HttpError as error:
        print("An error occurred: %s" % error)

    return events


if __name__ == "__main__":
    pass
    # print("Logging in and writing token.json")
    # events = get_events_for_week(pendulum.today("America/New_York"))
    # delete_all_events(events)
