import { execFileSync } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { fileURLToPath, URL } from 'node:url'

const repositoryRoot = fileURLToPath(new URL('../..', import.meta.url))
const databasePath =
  process.env.E2E_DATABASE_PATH ??
  fileURLToPath(new URL('../../backend/e2e.sqlite3', import.meta.url))
const environment = {
  ...process.env,
  DJANGO_SETTINGS_MODULE: 'config.settings.test',
  SQLITE_TEST_DB: databasePath,
}

function manage(...args: string[]): void {
  execFileSync(
    'uv',
    ['run', '--project', 'backend', 'python', 'backend/manage.py', ...args],
    {
      cwd: repositoryRoot,
      env: environment,
      stdio: 'inherit',
    },
  )
}

export default async function globalSetup(): Promise<void> {
  const password = randomBytes(24).toString('base64url')
  process.env.E2E_USER_PASSWORD = password
  manage('migrate', '--noinput')
  manage(
    'seed_demo_user',
    '--email',
    'e2e@example.invalid',
    '--username',
    'e2e',
    `--password=${password}`,
  )
  manage('seed_demo_context', '--email', 'e2e@example.invalid')
}
