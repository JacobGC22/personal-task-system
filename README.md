# Personal Task System

A lightweight personal task manager built on Supabase, GitHub Actions, and GitHub Pages.

## Setup Checklist

### 1. Supabase
- Create a free project at supabase.com
- Run the SQL in `supabase_setup.sql` in the SQL Editor
- Copy your project URL and anon key

### 2. GitHub Secrets
Add these three secrets under Settings > Secrets and Variables > Actions:
- `SUPABASE_URL` — your Supabase project URL
- `SUPABASE_KEY` — your Supabase anon key
- `RESEND_API_KEY` — your Resend API key

### 3. Update the Pages URL
In `send_task_email.py`, update this line with your actual GitHub username:
```python
PAGES_URL = 'https://YOUR_GITHUB_USERNAME.github.io/personal-task-system'
```

### 4. Enable GitHub Pages
Go to Settings > Pages > Source: Deploy from branch > Branch: main > Folder: / (root)

### 5. Add to iPhone Home Screen
- Open your Pages URL in Safari
- Tap Share > Add to Home Screen

### 6. Apple Shortcut (Add Task by Voice)
Create a new shortcut with these actions:
1. Ask for Input — "What's the task?" (text)
2. Ask for Input — "Due date? (leave blank to skip)" (text)
3. Get Contents of URL:
   - URL: https://YOUR_PROJECT.supabase.co/rest/v1/tasks
   - Method: POST
   - Headers: apikey = YOUR_ANON_KEY, Authorization = Bearer YOUR_ANON_KEY, Content-Type = application/json, Prefer = return=minimal
   - Body (JSON): {"task_name": "[Input 1]", "due_date": "[Input 2 or null]", "status": "open"}
4. Show notification: "Task added"

## Email Schedule
- 7am MDT
- 4pm MDT  
- 10pm MDT
