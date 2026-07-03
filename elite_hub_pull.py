#!/usr/bin/env python3
"""Pull Tom's Elite Hub data from Supabase cloud sync and summarize the week.

Sync account: tom@roserestoration.com. Sign-in is fully automated:
requests an email OTP, reads the code from Tom's work Gmail via API,
verifies, and stores the session at ~/Documents/GBP_Audit/.elite_hub_sb.json
(chmod 600). Later runs refresh silently. Manual fallback:
--request then --code NNNNNN.

Requires the Supabase project (tdgzcxqmrylrazeuizar) to be ACTIVE and
Tom signed into Cloud Sync on his phone with tom@roserestoration.com.

Usage: python3 elite_hub_pull.py [--raw|--request|--code NNNNNN]
"""
import json, os, re, sys, time, base64, urllib.request
from datetime import date, timedelta

SB = 'https://tdgzcxqmrylrazeuizar.supabase.co'
KEY = 'sb_publishable_9Bd_P3GLGZ5eMu66qEemlQ_PZ6WkVqi'
EMAIL = 'tom@roserestoration.com'
GTOKEN = os.path.expanduser('~/Documents/GBP_Audit/token.json')
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
    # No stored session: fully automated OTP via work Gmail
    since = time.time()
    sb('/auth/v1/otp', {'email': EMAIL, 'create_user': True})
    code = gmail_otp_code(since)
    s = sb('/auth/v1/verify', {'type': 'email', 'email': EMAIL, 'token': code})
    save_session(s)
    return s


def gmail_otp_code(since_ts):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    svc = build('gmail', 'v1', credentials=Credentials.from_authorized_user_file(GTOKEN))
    for _ in range(12):  # poll up to ~1 min
        msgs = svc.users().messages().list(userId='me', q='supabase OR "login code" OR "magic link" newer_than:1d',
                                           maxResults=5).execute().get('messages', [])
        for m in msgs:
            full = svc.users().messages().get(userId='me', id=m['id'], format='full').execute()
            if int(full['internalDate']) / 1000 < since_ts - 30:
                continue
            def walk(p):
                if p.get('body', {}).get('data'):
                    yield base64.urlsafe_b64decode(p['body']['data']).decode(errors='ignore')
                for sp in p.get('parts', []) or []:
                    yield from walk(sp)
            codes = re.findall(r'\b(\d{6})\b', ' '.join(walk(full['payload'])))
            if codes:
                return codes[0]
        time.sleep(5)
    raise RuntimeError('OTP email never arrived')


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
