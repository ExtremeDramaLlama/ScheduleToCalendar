# README

## Purpose

This program interacts with the tutor.com scheduling system and is used for importing the schedule into Google Calender. This readme assumes you're a programmer or at least a computer nerd of some kind -- the setup to use this program is a bit technical.

## Setup

To run, you'll need three sets of secrets.

1. `secrets/client_secrets.json`: You'll need to sign up for a google developer account. This is free and fairly straightforward. You'll create a project, enable the Calendar API, and then download the `client_screts.json` file that it generates. You'll probably want to set the pbulishing status to "in production", otherwise the login token wil expire every week and you'll need to log back in when running this program.
2. `secrets/login_credentials.json`: this will be your tutor.com username and password, as well as the `user_id` and `program_id`. The latter two can be obtained from the URL of the schedule login page. Look at the end of the URL, and you'll see them. Ignore the `%26`, that's the URL encoded `&`. 
3. Your calender ID, which you can get by clicking the triple dots (`⋮`) next the the calendar name, under `My calendars`, then `settings and sharings` and scroll down until you see the ID. You'll want to make a new calendar, because this program is configured to delete all events for a given week before adding new ones. To create a new calendar from the web interface, click the plus sign next to `Other calendars` on the left. Anyway, this ID is also stored in `login_credentials.json`. 

## Using

### "Installing"

You can install the requirements with `pip install -r requirements.txt`, then run the program with `python schedule_to_calendar.py`. 

To run in a venv:

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements
python schedule_to_calendar.py
```

### First Run

On the first run, it will open a web browser and prompt you to login to your google account and authorize this program to access your calendar. After login, it creates a `secrets/token.json` that contains a token that will let this program log back in as you, and that token should last forever, until you manually revoke it from your Security page in your Google account. (Assuming you set the status to "in production"; otherwise it will expire in a week.)

### Usage

To add the current week's schedule to your calendar, simply run `schedule_to_calendar.py`. To add next week's schedule, run with the `--next` argument. To add an arbitrary week's schedule, use the `--week <date>` option, where `<date>` is any date from that week, in the form of `mm/dd/yyyy`.

### Warning

When adding a week, it first deletes all the events from that week, then adds the new ones. This is an unsophisticated way of ensuring there are no duplicates, and handles you dropping hours. This is why you really should set up a specific calender to house these events. 
