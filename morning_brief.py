#!/usr/bin/env python3
"""5:00 AM training brief -> tkuhn05@gmail.com.

Today's session from the 20-week Richmond plan, run-window weather,
tomorrow's preview, and an anchor line. Sundays append the coming
week's full schedule. Goes quiet after race day.

Runs via launchd: ~/Library/LaunchAgents/com.elitehub.morningbrief.plist
Test:  python3 morning_brief.py --test   (sends now)
"""
import base64, sys, json, urllib.request
from datetime import date, timedelta
from email.mime.text import MIMEText

sys.path.insert(0, '/Users/thomaskuhn/elite-hub')
from sync_calendar import WEEKS, PLAN_START, RACE_DAY, PHASES, LIFTS

TOKEN = '/Users/thomaskuhn/Documents/GBP_Audit/token.json'
TO = 'tkuhn05@gmail.com'
LAT, LON = 38.85, -77.30   # Fairfax VA — adjust if runs start elsewhere

ANCHORS = [
    "I don't negotiate with myself anymore. This is the last time.",
    "Consistency over intensity. Five easy runs beat three hard ones.",
    "Easy days easy. That's how you get to the start line healthy.",
    "The plan survives one missed easy run. It doesn't survive quitting.",
    "Protect the morning and the weight takes care of itself.",
    "You're not building a race. You're building the guy who shows up.",
]


def session_for(d):
    idx = (d - PLAN_START).days // 7
    if idx < 0 or idx >= len(WEEKS):
        return None, None
    dow = (d.weekday() + 1) % 7
    return WEEKS[idx], WEEKS[idx]['d'].get(dow)


def dont_for(d, wk, ses, wk_num):
    """Top context-aware DON'T for today (mirrors dontListFor in elite-hub.html)."""
    dow_js = (d.weekday() + 1) % 7
    if wk_num == len(WEEKS):
        if dow_js == 6:
            return "Don't go out under 10:25 pace. The first 6 miles will feel free. They are not. The race starts at 18."
        return "Nothing new this week. No new shoes, food, or workouts. Feeling flat or puffy = the taper working."
    if wk.get('sb'):
        return "Step-back week: don't add miles because you feel good. Adaptation happens during the pull-back, not the push."
    if wk['ph'] == 1:
        return "No workouts, no pace-chasing. If you can't hold a conversation, slow down — easy is the whole job right now."
    if dow_js == 5 and wk['d'].get(6) and wk['d'][6][1] >= 8:
        return "No heavy lower body today — tomorrow's long run pays for every ego set."
    if dow_js == 6 and ses and ses[1] >= 14:
        return "Don't run this unfueled — gel every 5 miles, with water, race-day brand only."
    if 7 <= d.month <= 9 and ses and ses[1]:
        return "Don't chase pace in this heat — 15-30 sec/mi slower at the same effort is correct execution, not weakness."
    return "Don't make up missed miles. The plan survives a missed easy run; stacked catch-up days cause injuries."


def weather():
    try:
        url = (f'https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}'
               '&hourly=temperature_2m,precipitation_probability,relative_humidity_2m'
               '&temperature_unit=fahrenheit&forecast_days=1&timezone=America%2FNew_York')
        h = json.load(urllib.request.urlopen(url, timeout=10))['hourly']
        i = 5  # 5 AM slot
        t, p, hu = h['temperature_2m'][i], h['precipitation_probability'][i], h['relative_humidity_2m'][i]
        t7 = h['temperature_2m'][7]
        return f"{round(t)}F at 5 AM ({round(t7)}F by 7), {hu}% humidity, {p}% rain chance"
    except Exception:
        return None


def main():
    today = date.today()
    if today > RACE_DAY:
        return
    wk, ses = session_for(today)
    if wk is None:
        return
    wk_num = (today - PLAN_START).days // 7 + 1
    dow = (today.weekday() + 1) % 7

    lines = []
    if today == RACE_DAY:
        subject = 'RACE DAY. Richmond. 26.2.'
        lines.append('<p style="font-size:1.1em"><b>Everything is banked. '
                     'Go out at 10:25-10:30 for six miles no matter how good it feels. '
                     'The race starts at mile 18.</b></p>')
    elif ses:
        label, mi, detail = ses
        subject = f'Wk {wk_num}/{len(WEEKS)} · {label} {mi}mi today' if mi else f'Wk {wk_num}/{len(WEEKS)} · {label} today'
        lines.append(f'<p><b>Today: {label}{f" — {mi} miles" if mi else ""}</b>'
                     f'{f"<br>{detail}" if detail else ""}</p>')
    else:
        subject = f'Wk {wk_num}/{len(WEEKS)} · Rest day'
        lines.append('<p><b>Rest day.</b> Feet up, frozen bottle roll, protein.</p>')

    lift = LIFTS.get(dow)
    if lift and today != RACE_DAY and wk_num < len(WEEKS):
        lines.append(f'<p>Lift: {lift}</p>')

    sb = ' — <b>step-back week</b>, absorb it, do not add miles' if wk.get('sb') else ''
    lines.append(f'<p>Week {wk_num}/{len(WEEKS)} · {PHASES[wk["ph"]]} phase · {wk["mi"]} mi planned{sb}</p>')

    w = weather()
    if w and ses and ses[1]:
        lines.append(f'<p>Run window: {w}</p>')

    if today != RACE_DAY:
        lines.append(f'<p style="color:#c0392b"><b>Don\'t:</b> {dont_for(today, wk, ses, wk_num)}</p>')

    # Tomorrow preview
    _, tom = session_for(today + timedelta(days=1))
    lines.append(f'<p style="color:#666">Tomorrow: '
                 f'{f"{tom[0]} {tom[1]}mi" if tom and tom[1] else (tom[0] if tom else "rest")}</p>')

    # Sunday: coming week at a glance
    if today.weekday() == 6:
        nwk, _ = session_for(today + timedelta(days=1))
        if nwk:
            nn = (today + timedelta(days=1) - PLAN_START).days // 7 + 1
            rows = ''
            for i, dn in [(1, 'Mon'), (2, 'Tue'), (3, 'Wed'), (4, 'Thu'), (5, 'Fri'), (6, 'Sat'), (0, 'Sun')]:
                s = nwk['d'].get(i)
                rows += f'<tr><td style="padding:2px 10px 2px 0"><b>{dn}</b></td><td>' + \
                        (f'{s[0]} {s[1]}mi' if s and s[1] else (s[0] if s else 'Rest')) + '</td></tr>'
            lines.append(f'<p><b>Week {nn} ahead ({nwk["mi"]} mi):</b></p><table>{rows}</table>')

    lines.append(f'<p style="font-style:italic;color:#888">"{ANCHORS[today.toordinal() % len(ANCHORS)]}"</p>')

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(TOKEN)
    svc = build('gmail', 'v1', credentials=creds)
    msg = MIMEText('<html><body style="font-family:-apple-system,sans-serif">' + '\n'.join(lines) + '</body></html>', 'html')
    msg['To'] = TO
    msg['Subject'] = subject
    svc.users().messages().send(userId='me', body={'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}).execute()
    print('sent:', subject)


if __name__ == '__main__':
    main()
