import os
import requests
import pytz
from datetime import datetime, date

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
RESEND_API_KEY = os.environ['RESEND_API_KEY']
FORCE_SEND = os.environ.get('FORCE_SEND', '')  # 'morning', 'followup', or ''

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

# Valid Mountain time windows for each send
MORNING_HOUR = 7
MORNING_WINDOW = (55, 65)   # 6:55am - 7:05am Mountain (minutes from midnight edge)
FOLLOWUP_HOUR = 16
FOLLOWUP_MINUTE = 30
FOLLOWUP_WINDOW = 10        # +/- 10 minutes from 4:30pm Mountain


def get_mountain_now():
    return datetime.now(MOUNTAIN)


def get_mountain_today():
    return get_mountain_now().strftime('%Y-%m-%d')


def determine_send_type():
    """
    Returns 'morning', 'followup', or None.
    If FORCE_SEND is set (manual trigger), use that directly.
    Otherwise check Mountain time to determine which send this is.
    """
    if FORCE_SEND == 'morning':
        print('STATUS: Manual trigger — forcing morning email')
        return 'morning'
    if FORCE_SEND == 'followup':
        print('STATUS: Manual trigger — forcing followup email')
        return 'followup'

    now_mt = get_mountain_now()
    hour = now_mt.hour
    minute = now_mt.minute
    total_minutes = hour * 60 + minute

    morning_target = MORNING_HOUR * 60
    followup_target = FOLLOWUP_HOUR * 60 + FOLLOWUP_MINUTE

    # Check morning window (6:55am - 7:05am)
    if abs(total_minutes - morning_target) <= 5:
        print(f'STATUS: Mountain time is {hour}:{minute:02d} — matched morning window')
        return 'morning'

    # Check followup window (4:20pm - 4:40pm)
    if abs(total_minutes - followup_target) <= 10:
        print(f'STATUS: Mountain time is {hour}:{minute:02d} — matched followup window')
        return 'followup'

    print(f'STATUS: Mountain time is {hour}:{minute:02d} — outside all send windows, skipping')
    return None


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
            <a href="{snooze_url}" style="display:inline-block;padding:4px 10px;border:1px solid {BORDER};border-radius:6px;font-size:12px;color:{MUTED};text-decoration:none;font-family:'DM Sans',Arial,sans-serif;">
              Snooze 1 day
            </a>
          </td>
        </tr>'''

    return f'''
    <tr>
      <td style="padding:0 0 10px 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:{WHITE};border:1px solid {BORDER};border-radius:10px;{left_border}">
          <tr>
            <td style="padding:18px 20px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-size:15px;font-weight:500;color:#1a1a1a;font-family:'DM Sans',Arial,sans-serif;line-height:1.4;">
                    {task['task_name']}
                  </td>
                  <td align="right" style="white-space:nowrap;padding-left:16px;">
                    <a href="{complete_url}" style="display:inline-block;padding:7px 16px;background:{GREEN};color:{WHITE};text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;font-family:'DM Sans',Arial,sans-serif;">
                      Done
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


def build_email(tasks, send_type):
    today_str = get_mountain_now().strftime('%B %-d, %Y')
    time_label = '7am' if send_type == 'morning' else '4:30pm'

    skip_url = f"{PAGES_URL}/skip_followup.html"

    if not tasks:
        body_html = f'''
        <tr>
          <td align="center" style="padding:40px 0;color:{MUTED};font-size:15px;font-family:'DM Sans',Arial,sans-serif;">
            No open tasks. Nice work.
          </td>
        </tr>
        '''
    else:
        body_html = ''.join(build_task_row(t) for t in tasks)

    overdue_count = sum(1 for t in tasks if get_due_status(t.get('due_date')) == 'overdue')
    today_count = sum(1 for t in tasks if get_due_status(t.get('due_date')) == 'today')

    summary_parts = []
    if overdue_count:
        summary_parts.append(f'<span style="color:{DANGER};font-weight:600;">{overdue_count} overdue</span>')
    if today_count:
        summary_parts.append(f'<span style="color:#8A6A00;font-weight:600;">{today_count} due today</span>')
    summary_parts.append(f'{len(tasks)} total open')
    summary_html = ' &nbsp;·&nbsp; '.join(summary_parts)

    # Skip followup button — only in morning email
    skip_html = ''
    if send_type == 'morning':
        skip_html = f'''
          <tr>
            <td style="padding:20px 0 0 0;text-align:center;">
              <a href="{skip_url}" style="color:{MUTED};font-size:12px;text-decoration:none;border:1px solid {BORDER};padding:6px 14px;border-radius:6px;font-family:'DM Sans',Arial,sans-serif;">
                Skip today's followup email
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
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG};padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="padding:0 0 28px 0;">
              <div style="font-size:20px;font-weight:600;color:{GREEN};">Tasks</div>
              <div style="font-size:13px;color:{MUTED};margin-top:4px;">{time_label} &nbsp;·&nbsp; {today_str}</div>
            </td>
          </tr>

          <!-- Summary bar -->
          <tr>
            <td style="padding:0 0 20px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background:{WHITE};border:1px solid {BORDER};border-radius:10px;">
                <tr>
                  <td style="padding:14px 20px;font-size:13px;font-family:'DM Sans',Arial,sans-serif;">
                    {summary_html}
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Task rows -->
          <tr>
            <td>
              <table width="100%" cellpadding="0" cellspacing="0">
                {body_html}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:28px 0 0 0;text-align:center;">
              <a href="{PAGES_URL}" style="color:{GREEN};font-size:13px;font-weight:500;text-decoration:none;">
                Open task list →
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
    # Determine what to send
    send_type = determine_send_type()

    if send_type is None:
        print('STATUS: Nothing to send, exiting cleanly')
        return

    # Skip followup on weekends
    if send_type == 'followup' and is_weekend():
        print('STATUS: Weekend — skipping followup email')
        return

    # Skip followup if user pressed skip button today
    if send_type == 'followup' and check_followup_skipped():
        return

    # Prevent double-send on DST transition days (skip for manual triggers)
    if not FORCE_SEND:
        if check_already_sent_today(send_type):
            return

    # Fetch tasks
    print('STATUS: Fetching tasks from Supabase...')
    tasks = fetch_tasks()
    print(f'STATUS: Found {len(tasks)} open tasks')

    # Build and send
    html = build_email(tasks, send_type)
    send_email(html, send_type, len(tasks))

    # Mark as sent (skip for manual triggers to allow re-testing)
    if not FORCE_SEND:
        mark_sent_today(send_type)


if __name__ == '__main__':
    main()
