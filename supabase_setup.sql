-- Run this in Supabase SQL Editor

CREATE TABLE tasks (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  task_name text NOT NULL,
  due_date date,
  status text DEFAULT 'open',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations with anon key"
ON tasks
FOR ALL
USING (true)
WITH CHECK (true);
