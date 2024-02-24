# An example of a script you can use to run this easily. Personally I have it pinned to my
# start menu, but you could even set up windows to run it automatically every week if you wanted.
cd "C:\Users\Your Username\path\to\this\repository"
# Activate Virtual Envrionrment
# Assumes you already created this -- see https://docs.python.org/3/library/venv.html
.\venv\Scripts\Activate.ps1
# Run calendar sync for this week...
echo "Running schedular for this week"
python .\schedule_to_calendar.py
# and next.
echo "Running schedular for next week"
python .\schedule_to_calendar.py --next
