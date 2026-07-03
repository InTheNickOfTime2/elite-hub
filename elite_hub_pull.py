#!/usr/bin/env python3
"""Pull Tom's Elite Hub data from Supabase cloud sync and summarize the week.

Sync account: tkuhn05@gmail.com (Tom's personal). First sign-in is a
two-step handshake because the OTP lands in an inbox scripts can't read:

  1) python3 elite_hub_pull.py --request     (emails a code to tkuhn05)
  2) python3 elite_hub_pull.py --code 123456 (verify + store session)

The session is stored at ~/Documents/GBP_Audit/.elite_hub_sb.json
(chmod 600) and refreshes silently on every later run.

Requires the Supabase project (tdgzcxqmrylrazeuizar) to be ACTIVE and
Tom signed into Cloud Sync on his phone with tkuhn05@gmail.com.

Usage: python3 elite_hub_pull.py [--raw|--request|--code NNNNNN]
"""
import json, os, sys, urllib.request
from datetime import date, timedelta

SB = 'https://tdgzcxqmrylrazeuizar.supabase.co'
KEY = 'sb_publishable_9Bd_P3GLGZ5eMu66qEemlQ_PZ6WkVqi'
EMAIL = 'tkuhn05@gmail.com'
CREDS = os.path.expanduser('~/Documents/GBP_Audit/.elite_hub_sb.json')


def sb(path, body=None, bearer=None, method=None):
    headers = {'apikey': KEY, 'Content-Type': 'application/json'}
    if bearer:
        headers['Authorization'] = 'Bearer ' + bearer
    req = urllib.request.Request(SB + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def get_session():
    if '--request' in sys.argv:
        sb('/auth/v1/otp', {'email': EMAIL, 'create_user': True})
        print(f'Code sent to {EMAIL}. Rerun with: --code NNNNNN')
        sys.exit(0)
    if '--code' in sys.argv:
        code = sys.argv[sys.argv.index('--code') + 1]
        s = sb('/auth/v1/verify', {'type': 'email', 'email': EMAIL, 'token': code.strip()})
        save_session(s)
        print('Session stored. Future runs are automatic.')
        return s
    if os.path.exists(CREDS):
        saved = json.load(open(CREDS))
        try:
            s = sb('/auth/v1/token?grant_type=refresh_token', {'refresh_token': saved['refresh_token']})
            save_session(s)
            return s
        except Exception:
            print('Stored session expired — redo the handshake: --request, then --code NNNNNN')
            sys.exit(1)
    print('No session. Start with: python3 elite_hub_pull.py --request')
    sys.exit(1)


def save_session(s):
    json.dump({'refresh_token': s['refresh_token'], 'user_id': s['user']['id']}, open(CREDS, 'w'))
    os.chmod(CREDS, 0o600)


def main():
    s = get_session()
    rows = sb(f"/rest/v1/user_data?select=data,updated_at&user_id=eq.{s['user']['id']}", bearer=s['access_token'])
    if not rows:
        print('No synced data yet — has Tom signed into Cloud Sync on his phone?')
        return
    blob, updated = rows[0]['data'], rows[0]['updated_at']
    if '--raw' in sys.argv:
        print(json.dumps(blob, indent=1)[:8000])
        return
    g = lambda k: json.loads(blob.get('eh_' + k) or '{}')
    print(f'synced: {updated}  ({len(blob)} keys)\n')
    print('== last 7 days ==')
    runs = wt = slp = 0
    run_mi = 0.0
    for i in range(7):
        d = (date.today() - timedelta(days=i)).isoformat()
        r, w, sl, st, sc = g('run_' + d), g('wt_' + d), g('slp_' + d), g('steps_' + d), g('sc_' + d)
        mi = float(r.get('miles') or 0)
        if mi:
            runs += 1
            run_mi += mi
        parts = []
        if mi: parts.append(f"run {mi}mi" + (f"/{r.get('timeMin')}min" if r.get('timeMin') else ''))
        if w.get('lbs'): parts.append(f"{w['lbs']} lbs"); wt += 1
        if sl.get('hours'): parts.append(f"sleep {sl['hours']}h"); slp += 1
        if st.get('count'): parts.append(f"{st['count']} steps")
        if sc.get('protein'): parts.append(f"protein {sc['protein']}g tier")
        print(f"{d}: " + (' · '.join(parts) if parts else '—'))
    print(f'\nruns {runs} ({run_mi:.1f} mi) · weigh-ins {wt} · sleep logged {slp}')


if __name__ == '__main__':
    main()
