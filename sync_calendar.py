#!/usr/bin/env python3
"""Push Elite Hub planned runs + lifts to Tom's personal calendar.

Creates events on tom@roserestoration.com (OAuth token) with
tkuhn05@gmail.com as a silent attendee, so everything shows on the
personal calendar. Events are tagged (private extended property
ehub=1) so re-running the script wipes and recreates cleanly —
edit the plan, rerun, no duplicates.

Usage:  python3 sync_calendar.py [--from YYYY-MM-DD] [--to YYYY-MM-DD]
Defaults: tomorrow -> race day (2026-11-14).
"""
import sys, time, argparse
from datetime import date, datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN = '/Users/thomaskuhn/Documents/GBP_Audit/token.json'
CAL = 'primary'                    # tom@roserestoration.com
ATTENDEE = 'tkuhn05@gmail.com'     # Tom personal — events land here
TZ = 'America/New_York'
PLAN_START = date(2026, 4, 20)     # Week 1 Monday
RACE_DAY = date(2026, 11, 14)

RUN_TIME = (5, 30)    # 5:30 AM
LIFT_TIME = (17, 0)   # 5:00 PM

# Coach's 30-week plan — day-of-week (0=Sun..6=Sat): (label, miles, detail)
# Mirrors MARATHON_PLAN in elite-hub.html. Keep the two in sync.
WEEKS = [
 {'mi':15,'ph':1,'d':{2:('Easy Run',3,''),3:('XT',0,'Bike or swim 30-40 min'),4:('Easy Run',3,''),6:('Long Run',5,'Easy pace'),0:('Easy Run',4,'')}},
 {'mi':18,'ph':1,'d':{2:('Easy Run',3.5,''),3:('Easy Run',3,''),4:('Easy Run',4,''),6:('Long Run',5,'Easy pace'),0:('Easy Run',3,'')}},
 {'mi':21,'ph':1,'d':{2:('Easy + Strides',4,'Easy run + 4 strides'),3:('Easy Run',3,''),4:('Easy Run',4,''),6:('Long Run',6,'Easy pace'),0:('Easy Run',4,'')}},
 {'mi':18,'ph':1,'sb':1,'d':{2:('Easy Run',3,''),3:('XT',0,'XT 30 min'),4:('Easy + Strides',4,'Easy run + 4 strides'),6:('Long Run',6,'Easy pace'),0:('Easy Run',3,'')}},
 {'mi':25,'ph':1,'d':{2:('Easy + Strides',5,'Easy run + 6 strides'),3:('Easy Run',4,''),4:('Easy Run',4,''),6:('Long Run',7,'Easy pace'),0:('Easy Run',4,'')}},
 {'mi':28,'ph':1,'d':{2:('Easy + Strides',5,'Easy run + 6 strides'),3:('Easy Run',4,''),4:('Easy Run',5,''),6:('Long Run',8,'Easy pace'),0:('Easy Run',4,'')}},
 {'mi':30,'ph':2,'d':{2:('Fartlek',6,'WU 1.5mi + 6 x 2 min ON (tempo effort) / 2 min OFF + CD 1.5mi'),3:('Easy Run',4,''),4:('Easy Run',5,''),6:('Long Run',9,'Easy pace'),0:('Easy Run',4,'')}},
 {'mi':32,'ph':2,'d':{2:('Fartlek',7,'WU 1.5mi + 8 x 2 min ON / 2 min OFF + CD 1.5mi'),3:('Easy Run',4,''),4:('Easy + Strides',5,'Easy run + 6 strides'),6:('Long Run',10,'Easy pace — first double-digit'),0:('Easy Run',4,'')}},
 {'mi':28,'ph':2,'sb':1,'d':{2:('Easy + Strides',5,'Easy run + 6 strides'),3:('Easy Run',4,''),4:('Easy Run',4,''),6:('Long Run',8,'Easy pace'),0:('Easy Run',3,'Easy run or XT')}},
 {'mi':34,'ph':2,'d':{2:('Tempo',6.5,'WU 2mi + 15 min continuous tempo + CD 1.5mi'),3:('Easy Run',4,''),4:('Easy + Strides',5.5,'Easy run + 6 strides'),6:('Long Run',11,'Easy pace'),0:('Easy Run',4,'')}},
 {'mi':35,'ph':2,'d':{2:('Tempo',7,'WU 2mi + 20 min continuous tempo + CD 1.5mi'),3:('Easy Run',4,''),4:('Easy Run',5,''),6:('Long Run',12,'Easy pace'),0:('Easy Run',4,'')}},
 {'mi':36,'ph':2,'d':{2:('Tempo',7,'WU 2mi + 2 x 10 min tempo (2 min jog) + CD 1.5mi'),3:('Easy Run',5,''),4:('Easy + Strides',5,'Easy run + 6 strides'),6:('Long Run',13,'Easy pace'),0:('Easy Run',4,'')}},
 {'mi':38,'ph':3,'d':{2:('Tempo',7,'WU 2mi + 3 x 1 mile at tempo (90 sec jog) + CD 1.5mi'),3:('Easy Run',5,''),4:('Hills',5,'WU 1.5mi + 6 x 90 sec hill repeats (jog down) + CD 1.5mi'),6:('Long Run',13,'Easy pace'),0:('Easy Run',4,'')}},
 {'mi':40,'ph':3,'d':{2:('Tempo',8,'WU 2mi + 4 x 1 mile at tempo (90 sec jog) + CD 1.5mi'),3:('Easy Run',5,''),4:('Hills',5.5,'WU 1.5mi + 8 x 90 sec hill repeats (jog down) + CD 1.5mi'),6:('Long Run',14,'12 easy + last 2 moderate pickup'),0:('Easy Run',4,'')}},
 {'mi':34,'ph':3,'sb':1,'d':{2:('Tempo',5.5,'WU 1.5mi + 15 min tempo + CD 1.5mi'),3:('Easy Run',4,''),4:('Easy + Strides',5,'Easy run + 6 strides'),6:('Long Run',10,'Easy pace'),0:('Easy Run',4,'')}},
 {'mi':42,'ph':3,'d':{2:('Cruise Intervals',8,'WU 2mi + 5 x 5 min at tempo (60 sec jog) + CD 1.5mi'),3:('Easy Run',5,''),4:('Intervals',6,'WU 1.5mi + 6 x 800m at interval effort (400m jog) + CD 1.5mi'),6:('Long Run',15,'13 easy + last 2 moderate'),0:('Easy Run',4,'')}},
 {'mi':42,'ph':3,'d':{2:('Tempo',8,'WU 2mi + 25 min continuous tempo + CD 1.5mi'),3:('Easy Run',5,''),4:('Intervals',6,'WU 1.5mi + 5 x 1K at interval effort (400m jog) + CD 1.5mi'),6:('Long Run',16,'14 easy + last 2 pickup'),0:('Easy Run',4,'')}},
 {'mi':36,'ph':3,'sb':1,'d':{2:('Easy + Strides',5,'Easy run + 8 strides'),3:('Easy Run',4,''),4:('Tempo',5,'WU 1.5mi + 15 min tempo + CD 1.5mi'),6:('Long Run',12,'Easy — or 10K tune-up race this window'),0:('Easy Run',4,'')}},
 {'mi':42,'ph':4,'d':{2:('Tempo',8,'WU 2mi + 4 x 1 mile at tempo (90 sec jog) + CD 1.5mi'),3:('Easy Run',5,''),4:('Easy + Strides',5,'Easy run + 6 strides'),6:('MP Long Run',16,'10 easy + 4 at MP + 2 easy — practice fueling'),0:('Recovery Run',4,'')}},
 {'mi':44,'ph':4,'d':{2:('MP Repeats',9,'WU 2mi + 3 x 2 miles at MP (2 min jog) + CD 1.5mi'),3:('Easy Run',5,''),4:('Easy Run',5,''),6:('MP Long Run',17,'8 easy + 6 at MP + 3 easy — fuel every 5 mi'),0:('Recovery Run',4,'')}},
 {'mi':38,'ph':4,'sb':1,'d':{2:('Tempo',6,'WU 1.5mi + 20 min tempo + CD 1.5mi'),3:('Easy Run',4,''),4:('Easy + Strides',5,'Easy run + 6 strides'),6:('Long Run',12,'Easy, no MP'),0:('Easy Run',4,'')}},
 {'mi':45,'ph':4,'d':{2:('Tempo',9,'WU 2mi + 5 x 1 mile at tempo (90 sec jog) + CD 1.5mi'),3:('Easy Run',5,''),4:('Easy Run',5,''),6:('MP Long Run',18,'8 easy + 8 at MP + 2 easy — statement workout'),0:('Recovery Run',4,'')}},
 {'mi':46,'ph':4,'d':{2:('MP Repeats',10,'WU 2mi + 2 x 3 miles at MP (3 min jog) + CD 1.5mi'),3:('Easy Run',5,''),4:('Easy + Strides',5,'Easy run + 6 strides'),6:('MP Long Run',20,'10 easy + 8 at MP + 2 easy — FIRST 20-MILER'),0:('Recovery Run',3,'Recovery run or XT')}},
 {'mi':38,'ph':4,'sb':1,'d':{2:('Fartlek',6,'WU 1.5mi + 6 x 2 min (tempo effort) / 2 min jog + CD 1.5mi'),3:('Easy Run',4,''),4:('Easy Run',5,''),6:('Long Run',13,'Easy — or half marathon tune-up this window'),0:('Easy Run',4,'')}},
 {'mi':48,'ph':4,'d':{2:('Tempo',9,'WU 2mi + 4 x 2K at tempo (90 sec jog) + CD 1.5mi'),3:('Easy Run',5,''),4:('Easy + Strides',5,'Easy run + 6 strides'),6:('MP Long Run',21,'THE BIG ONE: 8 easy + 10 at MP + 2-4 easy — PEAK WEEK'),0:('Recovery Run',3,'Recovery run or XT')}},
 {'mi':40,'ph':4,'d':{2:('MP Repeats',9,'WU 2mi + 3 x 2 miles at MP (2 min jog) + CD 1.5mi'),3:('Easy Run',5,''),4:('Easy Run',5,''),6:('MP Long Run',16,'8 easy + 6 at MP + 2 easy'),0:('Easy Run',4,'')}},
 {'mi':38,'ph':4,'d':{2:('Tempo + MP',8,'WU 2mi + 20 min tempo + 10 min easy + 10 min at MP + CD 1.5mi'),3:('Easy Run',5,''),4:('Easy + Strides',5,'Easy run + 6 strides'),6:('Dress Rehearsal',14,'6 easy + 6 at MP + 2 easy — race shoes, kit, breakfast, fuel'),0:('Easy Run',4,'')}},
 {'mi':30,'ph':5,'d':{2:('MP Repeats',7,'WU 1.5mi + 4 x 1 mile at MP (90 sec jog) + CD 1mi'),3:('Easy Run',4,''),4:('Easy + Strides',4,'Easy run + 4 strides'),6:('Long Run',10,'Easy pace — taper begins'),0:('Easy Run',3,'')}},
 {'mi':24,'ph':5,'d':{2:('MP Repeats',6,'WU 1.5mi + 3 x 1 mile at MP (90 sec jog) + CD 1mi'),3:('Easy Run',3,''),4:('Easy + Strides',4,'Easy run + 6 strides'),6:('Easy Run',6,''),0:('Easy Run',3,'')}},
 {'mi':12,'ph':5,'d':{1:('Easy + Strides',3,'Easy run + 4 strides'),2:('MP Repeats',4,'WU 1mi + 2 x 1 mile at MP (2 min jog) + CD 1mi'),3:('Easy Run',3,''),4:('Shakeout',2,'Easy shakeout + 4 strides'),6:('RACE DAY',26.2,'RICHMOND MARATHON — negative split: 10:25-10:30 miles 1-6, settle to 10:18, finish strong')}},
]

PHASES = {1:'Base',2:'Aerobic',3:'Strength & Stamina',4:'Marathon Specific',5:'Taper'}

# Lift split (matches Elite Hub PROGRAMS, dow 1-6, Sunday rest)
LIFTS = {1:'Push A — Chest · Shoulders · Triceps',2:'Pull A — Back · Biceps',3:'Legs A — Quads · Glutes',
         4:'Push B — Shoulders · Chest · Triceps',5:'Pull B — Back · Biceps · Core',6:'Legs B — Hamstrings · Glutes · Calves'}
LIFT_PHASE_NOTE = {1:'',2:'',3:'Coach: Phase 3 — drop to 3 lift days, keep legs moderate.',
                   4:'Coach: Phase 4 — 2 maintenance lifts/week. Running is the priority.',
                   5:'Coach: Taper — light or none. Bank the fitness.'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='start', default=None)
    ap.add_argument('--to', dest='end', default=None)
    args = ap.parse_args()
    start = datetime.strptime(args.start, '%Y-%m-%d').date() if args.start else date.today() + timedelta(days=1)
    end = datetime.strptime(args.end, '%Y-%m-%d').date() if args.end else RACE_DAY

    creds = Credentials.from_authorized_user_file(TOKEN)
    svc = build('calendar', 'v3', credentials=creds)

    # Wipe previously synced events in range (idempotent resync)
    deleted = 0
    page = None
    while True:
        resp = svc.events().list(calendarId=CAL, privateExtendedProperty='ehub=1',
                                 timeMin=f'{start}T00:00:00-05:00', timeMax=f'{end + timedelta(days=1)}T00:00:00-05:00',
                                 maxResults=250, pageToken=page).execute()
        for ev in resp.get('items', []):
            svc.events().delete(calendarId=CAL, eventId=ev['id'], sendUpdates='none').execute()
            deleted += 1
        page = resp.get('nextPageToken')
        if not page:
            break
    print(f'cleared {deleted} previously synced events')

    created = 0
    d = start
    while d <= end:
        wk_idx = (d - PLAN_START).days // 7
        dow = (d.weekday() + 1) % 7  # python Mon=0 -> our Sun=0
        events = []
        if 0 <= wk_idx < len(WEEKS):
            w = WEEKS[wk_idx]
            ses = w['d'].get(dow)
            if ses:
                label, mi, detail = ses
                dur_min = 30 if mi == 0 else max(45, int(mi * 13) + 15)
                title = f'Run: {label} {mi}mi' if mi else f'Run day: {label}'
                if label == 'RACE DAY':
                    title = 'RICHMOND MARATHON — RACE DAY (26.2)'
                    dur_min = 330
                desc = (detail or label) + f"\n\nWeek {wk_idx+1}/30 — {PHASES[w['ph']]} phase"
                if w.get('sb'):
                    desc += ' (step-back week)'
                desc += f" — {w['mi']} mi planned this week.\nElite Hub tracks the details."
                events.append((RUN_TIME, dur_min, title, desc))
            lift = LIFTS.get(dow)
            if lift and wk_idx < 29 and label_is_not_race(w, dow):  # race week: no lifting
                note = LIFT_PHASE_NOTE[w['ph']]
                events.append((LIFT_TIME, 75, f'Lift: {lift.split(" — ")[0]}', lift + ('\n\n' + note if note else '')))
        for (hh, mm), dur, title, desc in events:
            begin = datetime(d.year, d.month, d.day, hh, mm)
            body = {
                'summary': title,
                'description': desc,
                'start': {'dateTime': begin.isoformat(), 'timeZone': TZ},
                'end': {'dateTime': (begin + timedelta(minutes=dur)).isoformat(), 'timeZone': TZ},
                'attendees': [{'email': ATTENDEE}],
                'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 30}]},
                'extendedProperties': {'private': {'ehub': '1'}},
            }
            svc.events().insert(calendarId=CAL, body=body, sendUpdates='none').execute()
            created += 1
            time.sleep(0.1)
        d += timedelta(days=1)
    print(f'created {created} events ({start} -> {end})')


def label_is_not_race(w, dow):
    ses = w['d'].get(dow)
    return not (ses and ses[0] == 'RACE DAY')


if __name__ == '__main__':
    main()
