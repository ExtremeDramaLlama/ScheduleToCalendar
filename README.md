# README

## Purpose

This program interacts with the tutor.com scheduling system and is (going to be) used for importing the schedule into Google Calender, and for automatically signing up for hours when they become available. 

## Setup

To run, you'll need three sets of secrets.

1. `secrets/client_secrets.json`: this will be from your google developer account, and is what allows you to access the Calendar API.
2. `secrets/login_credentials.json`: this will be your tutor.com username and password, as well as the `user_id` and `program_id`. The latter two can be obtained from the URL of the schedule login page
3. Your calender ID. You need to make a new calendar, because this program is configured to delete all events for a given week before adding new ones. This is also stored in `login_credentials.json`.

## Using

### First Run

On the first run, it will open a web browser and prompt you to login to your google account and authorize this program to access your calendar. After login, it creates a `secrets/token.json` that contains a token that will let this program log back in as you, and that token should last forever, until you manually revoke it from your Security page in your Google account.

### Usage

To add the current week's schedule to your calendar, simply run `add_to_calendar.py`. To add next week's schedule, run with the `next` argument. To add an arbitrary week's schedule, pass in any date from that that week, in the form of `mm/dd/yyyy`.

Note that when adding a week, it first deletes all the events from that week, then adds. This is an unsophisticated way of ensuring there are no duplicates, and handles you dropping hours. This is also why you really should set up a specific calender to house these events. 