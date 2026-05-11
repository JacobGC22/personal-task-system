import os
import requests
import pytz
from datetime import datetime, date

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
RESEND_API_KEY = os.environ['RESEND_API_KEY']
SEND_TYPE = os.environ.get('SEND_TYPE', '')  # 'morning' or 'followup'

PAGES_URL = 'https://JacobGC22.github.io/personal-task-system'

GREEN = '#1D4D2E'
GREEN_DARK = '#163D24'
GOLD = '#C8993A'
BG = '#F5F3EE'
WHITE = '#FFFFFF'
MUTED = '#888888'
DANGER = '#C0392B'
BORDER = '#E2DED6'

MOUNTAIN = pytz.timezone('America/Denver')


def get_mountain_now():
    return datetime.now(MOUNTAIN)


def get_mountain_today():
    return get_mountain_now().strftime('%Y-%m-%d')


def is_weekend():
    now_mt = get_mountain_now()
    is_wknd = now_mt.weekday() >= 5  # 5=Saturday, 6=Sunday
    print(f'STATUS: Day of week (Mountain): {now_mt.strftime("%A")} — weekend={is_wknd}')
    return is_wknd


def check_already_sent_today(send_type):
    """Check Supabase to see if we already sent this email today (prevents DST double-send)."""
    key = f'last_sent_{send_type}'
    today = get_mountain_today()

    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/settings?key=eq.{key}',
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }
    )
    res.raise_for_status()
    rows = res.json()

    if rows and rows[0]['value'].get('date') == today:
        print(f'STATUS: Already sent {send_type} email today ({today}), skipping')
        return True
    return False


def mark_sent_today(send_type):
    """Record that we sent this email today."""
    key = f'last_sent_{send_type}'
    today = get_mountain_today()

    # Upsert into settings
    res = requests.post(
        f'{SUPABASE_URL}/rest/v1/settings',
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates'
        },
        json={'key': key, 'value': {'date': today}}
    )
    res.raise_for_status()
    print(f'STATUS: Marked {send_type} as sent for {today}')


def check_followup_skipped():
    """Check if user has skipped the followup email for today."""
    today = get_mountain_today()

    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/settings?key=eq.skip_followup_date',
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }
    )
    res.raise_for_status()
    rows = res.json()

    if rows and rows[0]['value'].get('date') == today:
        print(f'STATUS: Followup skipped for today ({today})')
        return True
    print('STATUS: Followup not skipped, sending')
    return False


def fetch_tasks():
    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/tasks',
        params={
            'status': 'eq.open',
            'order': 'due_date.asc.nullslast,created_at.asc'
        },
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }
    )
    res.raise_for_status()
    return res.json()


def fetch_upcoming_birthdays():
    """Fetch birthdays occurring within the next 14 days including today."""
    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/birthdays',
        params={'order': 'month.asc,day.asc'},
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }
    )
    res.raise_for_status()
    all_birthdays = res.json()

    today_mt = get_mountain_now()
    today_date = today_mt.date()
    upcoming = []

    for b in all_birthdays:
        month = b['month']
        day = b['day']

        # Find next occurrence of this birthday
        try:
            this_year = date(today_date.year, month, day)
        except ValueError:
            continue  # Skip invalid dates like Feb 30

        if this_year < today_date:
            next_bday = date(today_date.year + 1, month, day)
        else:
            next_bday = this_year

        days_away = (next_bday - today_date).days

        if days_away <= 14:
            upcoming.append({
                'name': b['name'],
                'month': month,
                'day': day,
                'days_away': days_away,
                'date_str': next_bday.strftime('%B %-d')
            })

    upcoming.sort(key=lambda x: x['days_away'])
    return upcoming


def section_header(title, emoji=''):
    """Full-width green strip section header."""
    return f'''
          <tr>
            <td style="padding:0 0 12px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background:{GREEN};border-radius:8px;">
                <tr>
                  <td style="padding:10px 16px;">
                    <span style="font-size:12px;font-weight:700;color:{WHITE};text-transform:uppercase;letter-spacing:1px;font-family:'DM Sans',Arial,sans-serif;">{emoji}{title}</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>'''


def build_birthday_section(birthdays):
    if not birthdays:
        return ''

    rows = ''
    for b in birthdays:
        if b['days_away'] == 0:
            accent = GOLD
            label = f'<span style="color:#8A6A00;font-weight:600;font-size:12px;">🎂 Today!</span>'
        elif b['days_away'] <= 3:
            accent = GOLD
            label = f'<span style="color:#8A6A00;font-size:12px;font-weight:500;">In {b["days_away"]} day{"s" if b["days_away"] != 1 else ""} · {b["date_str"]}</span>'
        else:
            accent = BORDER
            label = f'<span style="color:{MUTED};font-size:12px;">In {b["days_away"]} days · {b["date_str"]}</span>'

        rows += f'''
        <tr>
          <td style="padding:0 0 8px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:{WHITE};border:1px solid {BORDER};border-left:3px solid {accent};border-radius:8px;">
              <tr>
                <td style="padding:12px 16px;">
                  <div style="font-size:15px;font-weight:600;color:#1a1a1a;font-family:'DM Sans',Arial,sans-serif;">{b["name"]}</div>
                  <div style="margin-top:3px;">{label}</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>'''

    return f'''
          {section_header('Birthdays', '🎂  ')}
          <tr>
            <td style="padding:0 0 24px 0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                {rows}
              </table>
            </td>
          </tr>
    '''


def fetch_upcoming_subscriptions():
    """Fetch subscriptions and trials due for reminder."""
    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/subscriptions',
        params={'order': 'next_billing_date.asc.nullslast'},
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }
    )
    res.raise_for_status()
    all_subs = res.json()

    today_date = date.fromisoformat(get_mountain_today())
    reminders = []

    for s in all_subs:
        cadence = s.get('cadence')

        if cadence == 'trial':
            end_date_str = s.get('trial_end_date')
            if not end_date_str:
                continue
            end_date = date.fromisoformat(end_date_str)
            days_away = (end_date - today_date).days
            if 0 <= days_away <= 14:
                reminders.append({
                    'name': s['name'],
                    'days_away': days_away,
                    'date_str': end_date.strftime('%b %-d'),
                    'type': 'trial',
                    'amount': None
                })

        elif cadence == 'monthly':
            billing_str = s.get('next_billing_date')
            if not billing_str:
                continue
            billing_date = date.fromisoformat(billing_str)
            days_away = (billing_date - today_date).days
            if 0 <= days_away <= 3:
                reminders.append({
                    'name': s['name'],
                    'days_away': days_away,
                    'date_str': billing_date.strftime('%b %-d'),
                    'type': 'monthly',
                    'amount': s['amount']
                })

        elif cadence == 'yearly':
            billing_str = s.get('next_billing_date')
            if not billing_str:
                continue
            billing_date = date.fromisoformat(billing_str)
            days_away = (billing_date - today_date).days
            if 0 <= days_away <= 14:
                reminders.append({
                    'name': s['name'],
                    'days_away': days_away,
                    'date_str': billing_date.strftime('%b %-d'),
                    'type': 'yearly',
                    'amount': s['amount']
                })

    reminders.sort(key=lambda x: x['days_away'])
    return reminders


def build_subscription_section(reminders):
    if not reminders:
        return ''

    rows = ''
    for r in reminders:
        if r['type'] == 'trial':
            accent = DANGER
            if r['days_away'] == 0:
                label = f'<span style="color:{DANGER};font-weight:600;font-size:12px;">Trial ends today — cancel now</span>'
            else:
                label = f'<span style="color:{DANGER};font-size:12px;">Trial ends in {r["days_away"]} day{"s" if r["days_away"] != 1 else ""} · {r["date_str"]}</span>'
        else:
            accent = GOLD
            amount_str = f'${float(r["amount"]):.2f}' if r["amount"] else ''
            cadence_str = '/mo' if r['type'] == 'monthly' else '/yr'
            if r['days_away'] == 0:
                label = f'<span style="color:#8A6A00;font-weight:600;font-size:12px;">Billing today · {amount_str}{cadence_str}</span>'
            else:
                label = f'<span style="color:{MUTED};font-size:12px;">Billing in {r["days_away"]} day{"s" if r["days_away"] != 1 else ""} · {r["date_str"]} · {amount_str}{cadence_str}</span>'

        rows += f'''
        <tr>
          <td style="padding:0 0 8px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:{WHITE};border:1px solid {BORDER};border-left:3px solid {accent};border-radius:8px;">
              <tr>
                <td style="padding:12px 16px;">
                  <div style="font-size:15px;font-weight:600;color:#1a1a1a;font-family:'DM Sans',Arial,sans-serif;">{r["name"]}</div>
                  <div style="margin-top:3px;">{label}</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>'''

    return f'''
          {section_header('Upcoming Billing', '💳  ')}
          <tr>
            <td style="padding:0 0 24px 0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                {rows}
              </table>
            </td>
          </tr>
    '''


def format_date(date_str):
    if not date_str:
        return None
    d = date.fromisoformat(date_str)
    return d.strftime('%b %-d, %Y')


def get_due_status(date_str):
    if not date_str:
        return None
    today = get_mountain_today()
    if date_str < today:
        return 'overdue'
    elif date_str == today:
        return 'today'
    return 'upcoming'


def build_task_row(task):
    status = get_due_status(task.get('due_date'))
    complete_url = f"{PAGES_URL}/complete.html?id={task['id']}"
    snooze_url = f"{PAGES_URL}/snooze.html?id={task['id']}" if task.get('due_date') else None

    due_html = ''
    if task.get('due_date'):
        if status == 'overdue':
            due_html = f'<div style="font-size:12px;color:{DANGER};font-weight:500;margin-top:4px;">Overdue · {format_date(task["due_date"])}</div>'
        elif status == 'today':
            due_html = f'<div style="font-size:12px;color:#8A6A00;font-weight:500;margin-top:4px;">Due Today</div>'
        else:
            due_html = f'<div style="font-size:12px;color:{MUTED};margin-top:4px;">Due {format_date(task["due_date"])}</div>'

    left_border = ''
    if status == 'overdue':
        left_border = f'border-left:3px solid {DANGER};'
    elif status == 'today':
        left_border = f'border-left:3px solid {GOLD};'

    snooze_html = ''
    if snooze_url:
        snooze_html = f'''
        <tr>
          <td colspan="2" style="padding-top:8px;">
            <a href="{snooze_url}" style="font-size:12px;color:{MUTED};text-decoration:none;font-family:'DM Sans',Arial,sans-serif;">
              Snooze 1 day →
            </a>
          </td>
        </tr>'''

    return f'''
    <tr>
      <td style="padding:0 0 8px 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:{WHITE};border:1px solid {BORDER};border-radius:8px;{left_border}">
          <tr>
            <td style="padding:14px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-size:15px;font-weight:600;color:#1a1a1a;font-family:'DM Sans',Arial,sans-serif;line-height:1.4;">
                    {task['task_name']}
                  </td>
                  <td align="right" style="white-space:nowrap;padding-left:16px;">
                    <a href="{complete_url}" style="display:inline-block;padding:6px 14px;background:{GREEN};color:{WHITE};text-decoration:none;border-radius:6px;font-size:12px;font-weight:700;font-family:'DM Sans',Arial,sans-serif;letter-spacing:0.3px;">
                      DONE
                    </a>
                  </td>
                </tr>
                {f'<tr><td colspan="2">{due_html}</td></tr>' if due_html else ''}
                {snooze_html}
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
    '''


def build_email(tasks, send_type, birthdays=None, subscription_reminders=None):
    today_str = get_mountain_now().strftime('%B %-d, %Y')
    time_label = '7am' if send_type == 'morning' else '4:30pm'

    skip_url = f"{PAGES_URL}/skip_followup.html"

    if not tasks:
        body_html = f'''
        <tr>
          <td align="center" style="padding:32px 0;color:{MUTED};font-size:14px;font-family:'DM Sans',Arial,sans-serif;">
            No open tasks. Nice work.
          </td>
        </tr>
        '''
    else:
        body_html = ''.join(build_task_row(t) for t in tasks)

    overdue_count = sum(1 for t in tasks if get_due_status(t.get('due_date')) == 'overdue')
    today_count = sum(1 for t in tasks if get_due_status(t.get('due_date')) == 'today')

    # Build task section header with inline summary
    status_parts = []
    if overdue_count:
        status_parts.append(f'<span style="color:{DANGER};font-weight:700;">{overdue_count} overdue</span>')
    if today_count:
        status_parts.append(f'<span style="color:{GOLD};font-weight:700;">{today_count} due today</span>')
    status_str = ' · '.join(status_parts)
    count_str = f'{len(tasks)} open'

    tasks_header = f'''
          <tr>
            <td style="padding:0 0 12px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background:{GREEN};border-radius:8px;">
                <tr>
                  <td style="padding:10px 16px;">
                    <span style="font-size:12px;font-weight:700;color:{WHITE};text-transform:uppercase;letter-spacing:1px;font-family:'DM Sans',Arial,sans-serif;">✓  Tasks</span>
                  </td>
                  <td align="right" style="padding:10px 16px;">
                    <span style="font-size:12px;color:rgba(255,255,255,0.75);font-family:'DM Sans',Arial,sans-serif;">{count_str}{" · " + status_str if status_str else ""}</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>'''

    birthday_html = build_birthday_section(birthdays or [])
    subscription_html = build_subscription_section(subscription_reminders or [])

    # Skip followup button — only in morning email
    skip_html = ''
    if send_type == 'morning':
        skip_html = f'''
          <tr>
            <td style="padding:24px 0 0 0;text-align:center;border-top:1px solid {BORDER};">
              <a href="{skip_url}" style="color:{MUTED};font-size:12px;text-decoration:none;font-family:'DM Sans',Arial,sans-serif;">
                Skip today's 4:30pm email
              </a>
            </td>
          </tr>'''

    return f'''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:{BG};font-family:'DM Sans',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG};padding:24px 16px 32px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="padding:0 0 24px 0;border-bottom:2px solid {GREEN};margin-bottom:24px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <div style="font-size:22px;font-weight:700;color:{GREEN};font-family:'DM Sans',Arial,sans-serif;letter-spacing:-0.5px;">Jacob Dashboard</div>
                    <div style="font-size:13px;color:{MUTED};margin-top:3px;font-family:'DM Sans',Arial,sans-serif;">{time_label} &nbsp;·&nbsp; {today_str}</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Spacer -->
          <tr><td style="height:20px;"></td></tr>

          {birthday_html}
          {subscription_html}

          {tasks_header}

          <!-- Task rows -->
          <tr>
            <td style="padding:0 0 8px 0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                {body_html}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 0 0 0;text-align:center;">
              <a href="{PAGES_URL}" style="color:{GREEN};font-size:13px;font-weight:600;text-decoration:none;font-family:'DM Sans',Arial,sans-serif;">
                Open Dashboard →
              </a>
            </td>
          </tr>

          {skip_html}

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
'''


def send_email(html, send_type, task_count):
    time_label = '7am' if send_type == 'morning' else '4:30pm'
    subject = f'Tasks · {time_label} · {task_count} open'
    if task_count == 0:
        subject = f'Tasks · {time_label} · All clear'

    res = requests.post(
        'https://api.resend.com/emails',
        headers={
            'Authorization': f'Bearer {RESEND_API_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            'from': 'onboarding@resend.dev',
            'to': ['jacob@goodmancampaigns.com'],
            'subject': subject,
            'html': html
        }
    )

    if res.status_code not in (200, 201):
        print(f'ERROR: Resend returned {res.status_code}: {res.text}')
        res.raise_for_status()
    else:
        print(f'SUCCESS: Email sent. Subject: {subject}')


def main():
    send_type = SEND_TYPE

    if send_type not in ('morning', 'followup'):
        print(f'STATUS: SEND_TYPE is "{send_type}" — must be morning or followup, exiting')
        return

    print(f'STATUS: Send type: {send_type}')

    # Skip followup on weekends
    if send_type == 'followup' and is_weekend():
        print('STATUS: Weekend — skipping followup email')
        return

    # Skip followup if user pressed skip button today
    if send_type == 'followup' and check_followup_skipped():
        return

    # Prevent double-send (e.g. both DST crons firing)
    if check_already_sent_today(send_type):
        return

    # Fetch tasks
    print('STATUS: Fetching tasks from Supabase...')
    tasks = fetch_tasks()
    print(f'STATUS: Found {len(tasks)} open tasks')

    # Fetch birthdays (only for morning email)
    birthdays = []
    if send_type == 'morning':
        print('STATUS: Fetching upcoming birthdays...')
        birthdays = fetch_upcoming_birthdays()
        print(f'STATUS: Found {len(birthdays)} upcoming birthdays in next 14 days')

    # Fetch subscription reminders (only for morning email)
    subscription_reminders = []
    if send_type == 'morning':
        print('STATUS: Fetching subscription reminders...')
        subscription_reminders = fetch_upcoming_subscriptions()
        print(f'STATUS: Found {len(subscription_reminders)} subscription reminders')

    # Build and send
    html = build_email(tasks, send_type, birthdays, subscription_reminders)
    send_email(html, send_type, len(tasks))

    # Mark as sent
    mark_sent_today(send_type)


if __name__ == '__main__':
    main()
