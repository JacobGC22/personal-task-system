import os
import requests
from datetime import date, datetime

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
RESEND_API_KEY = os.environ['RESEND_API_KEY']

PAGES_URL = 'https://YOUR_GITHUB_USERNAME.github.io/personal-task-system'  # UPDATE THIS

NAVY = '#1B3A8C'
GOLD = '#F5A800'
BG = '#F7F6F2'
WHITE = '#FFFFFF'
MUTED = '#888888'
DANGER = '#C0392B'
SUCCESS = '#27AE60'
BORDER = '#E5E3DC'


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
    # Determine which send this is based on UTC hour
    hour = datetime.utcnow().hour
    if hour == 13:
        return '7am'
    elif hour == 22:
        return '4pm'
    elif hour == 4:
        return '10pm'
    return 'Task Update'


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

    due_html = ''
    if task.get('due_date'):
        if status == 'overdue':
            due_html = f'<div style="font-size:12px;color:{DANGER};font-weight:500;margin-top:3px;">Overdue · {format_date(task["due_date"])}</div>'
        elif status == 'today':
            due_html = f'<div style="font-size:12px;color:#C47A00;font-weight:500;margin-top:3px;">Due Today</div>'
        else:
            due_html = f'<div style="font-size:12px;color:{MUTED};margin-top:3px;">Due {format_date(task["due_date"])}</div>'

    left_border = ''
    if status == 'overdue':
        left_border = f'border-left:3px solid {DANGER};'
    elif status == 'today':
        left_border = f'border-left:3px solid {GOLD};'

    return f'''
    <tr>
      <td style="padding:0 0 8px 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:{WHITE};border:1px solid {BORDER};border-radius:10px;{left_border}">
          <tr>
            <td style="padding:14px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-size:15px;font-weight:500;color:#1a1a1a;font-family:'DM Sans',Arial,sans-serif;">
                    {task['task_name']}
                  </td>
                  <td align="right" style="white-space:nowrap;">
                    <a href="{complete_url}" style="display:inline-block;padding:6px 14px;background:{NAVY};color:{WHITE};text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;font-family:'DM Sans',Arial,sans-serif;">
                      Done
                    </a>
                  </td>
                </tr>
                {f'<tr><td colspan="2">{due_html}</td></tr>' if due_html else ''}
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
    no_due_count = sum(1 for t in tasks if not t.get('due_date'))

    summary_parts = []
    if overdue_count:
        summary_parts.append(f'<span style="color:{DANGER};font-weight:600;">{overdue_count} overdue</span>')
    if today_count:
        summary_parts.append(f'<span style="color:#C47A00;font-weight:600;">{today_count} due today</span>')
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
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG};padding:24px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="padding:0 0 24px 0;">
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td style="width:8px;background:{GOLD};border-radius:2px;">&nbsp;</td>
                  <td style="width:10px;"></td>
                  <td>
                    <div style="font-size:20px;font-weight:600;color:{NAVY};">Tasks</div>
                    <div style="font-size:13px;color:{MUTED};margin-top:2px;">{time_label} &nbsp;·&nbsp; {today_str}</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Summary bar -->
          <tr>
            <td style="padding:0 0 16px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background:{WHITE};border:1px solid {BORDER};border-radius:10px;">
                <tr>
                  <td style="padding:12px 16px;font-size:13px;font-family:'DM Sans',Arial,sans-serif;">
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
            <td style="padding:24px 0 0 0;text-align:center;">
              <a href="{PAGES_URL}" style="color:{NAVY};font-size:13px;font-weight:500;text-decoration:none;">
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
            'to': ['jacobpmalinowski@gmail.com'],
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
    print('Fetching tasks from Supabase...')
    tasks = fetch_tasks()
    print(f'Found {len(tasks)} open tasks')

    time_label = get_time_label()
    print(f'Send time: {time_label}')

    html = build_email(tasks, time_label)
    send_email(html, time_label, len(tasks))


if __name__ == '__main__':
    main()
