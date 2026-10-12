# CampusCanvas

CampusCanvas is a college creative-work showcase with student and faculty accounts, creator profiles, searchable posts, likes, comments, shares, follows, bookmarks, campus events, competition entries, and administrator moderation.

## Start the app in Replit

The web app and Flask API run as two services. Use Replit's Run/Preview controls to start both services. For a local shell, open two terminals and run:

```sh
pnpm --filter @workspace/api-server run dev
pnpm --filter @workspace/campuscanvas run dev
```

The API initializes its SQLite database on first start. It stores the database in `artifacts/api-server/campuscanvas/data/campuscanvas.sqlite3` and uploaded media in `artifacts/api-server/campuscanvas/static/uploads/`. Files are limited to 20 MB. Set `CAMPUSCANVAS_DB` to use a different SQLite file path.

## Create the first administrator

Registration intentionally allows only student or faculty roles. Create an administrator from the workspace root:

```sh
python3 artifacts/api-server/campuscanvas/manage.py create-admin
```

The command asks for a name, email, department, and password without echoing the password. Sign in at `/login`; the admin dashboard is available from the main navigation after signing in.

The app uses the `SESSION_SECRET` environment secret for signed, HTTP-only sessions. Keep it configured and private. Production sessions use secure cookies and should be served over HTTPS.

## Publish

Use Replit's Publish action for the CampusCanvas app. The frontend is built as a static site; the Flask API runs under `/api` with Gunicorn in production. After publishing, create the production administrator in the production app environment. Do not reuse a development database or copy administrator passwords into source files.

This project follows the report's SQLite and local-upload-folder architecture. SQLite and uploaded files are stored on the API server's local filesystem, so treat this as a single-instance deployment: confirm that the target deployment preserves those files, keep backups, and do not scale the API to multiple instances. For a larger public deployment, move the database and media to durable shared services before scaling.

## Content and safety

- Public feeds include approved posts only. New submissions start as pending.
- Admin roles are created with the command above; public registration cannot grant admin access.
- Passwords are hashed. Mutating API requests require a session CSRF token.
- Supported uploads include common images, video, audio, PDF, DOCX, and text files. SVG and executable/script formats are not accepted.
- Use the report and moderation tools to review inappropriate content and manage account access.
