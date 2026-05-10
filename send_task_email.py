import os
import requests
from datetime import date, datetime

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
RESEND_API_KEY = os.environ['RESEND_API_KEY']
SEND_HOUR_MDT = int(os.environ.get('SEND_HOUR_MDT', 0))

PAGES_URL = 'https://JacobGC22.github.io/personal-task-system'

GREEN = '#1D4D2E'
GREEN_DARK = '#163D24'
GOLD = '#C8993A'
BG = '#F5F3EE'
WHITE = '#FFFFFF'
MUTED = '#888888'
DANGER = '#C0392B'
BORDER = '#E2DED6'


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


def get_time_label():
    hour = SEND_HOUR_MDT
    if hour == 0:
        # Fallback if env var not set
        hour = datetime.utcnow().hour
    if hour < 12:
        return f'{hour}am'
    elif hour == 12:
        return '12pm'
    else:
        return f'{hour - 12}pm'


def format_date(date_str):
    if not date_str:
        return None
    d = date.fromisoformat(date_str)
    return d.strftime('%b %-d, %Y')


def get_due_status(date_str):
    if not date_str:
        return None
    today = date.today().isoformat()
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
        left_border = f'border-left:3px solid {DANGER};padding-left:0;'
    elif status == 'today':
        left_border = f'border-left:3px solid {GOLD};padding-left:0;'

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


def build_email(tasks, time_label):
    today_str = date.today().strftime('%B %-d, %Y')

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

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
'''


def send_email(html, time_label, task_count):
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
    print(f'Send hour MDT: {SEND_HOUR_MDT}')
    print('Fetching tasks from Supabase...')
    tasks = fetch_tasks()
    print(f'Found {len(tasks)} open tasks')

    time_label = get_time_label()
    print(f'Time label: {time_label}')

    html = build_email(tasks, time_label)
    send_email(html, time_label, len(tasks))


if __name__ == '__main__':
    main()
