# Academic Compliance System

Academic compliance monitoring for university administrators, academic officers, lecturers, and students.

## Local URLs

- Dashboard: http://localhost:5173
- API health: http://localhost:4000/health
- PostgreSQL: localhost:5432

## Start The System

Build once:

```powershell
npm.cmd run build
```

Start independently from VS Code:

```powershell
npm.cmd start
```

Register automatic startup when you sign in to Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register-startup.ps1
```

PostgreSQL runs as the `postgresql-x64-16` Windows service. It should remain available even when VS Code is closed. The API and dashboard started by `start-system.ps1` run as detached Node processes.

## Development Database

The local database is configured in `server/.env`:

```text
Host: localhost
Port: 5432
Database: academic_compliance
User: academic
Password: academic
```

Apply the current Prisma schema:

```powershell
Push-Location server
.\node_modules\.bin\prisma.cmd db push
.\node_modules\.bin\tsx.cmd prisma\seed.ts
Pop-Location
```

Development administrator:

```text
Email: admin@university.edu
Password: Admin@12345
```

Change this password before using the system outside local development.

## Viewing The Database

### pgAdmin

Install pgAdmin, create a server connection with the values above, then browse:

`Servers > localhost > Databases > academic_compliance > Schemas > public > Tables`

### PostgreSQL command line

```powershell
$env:PGPASSWORD = "academic"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U academic -d academic_compliance
```

Useful queries:

```sql
SELECT * FROM "User";
SELECT * FROM "Student";
SELECT * FROM "ComplianceRecord";
SELECT * FROM "Notification" ORDER BY "createdAt" DESC;
SELECT * FROM "AuditLog" ORDER BY "createdAt" DESC;
```

## Main Features

- Role-aware login for administrators, academic officers, lecturers, and students
- Student compliance monitoring and risk review
- Attendance, marks, grades, assessments, and course offerings API
- Student and lecturer workspaces
- Rules and threshold management
- User and staff management
- Reports and CSV export
- Profile, notifications, preferences, and audit log
- Local academic assistant
