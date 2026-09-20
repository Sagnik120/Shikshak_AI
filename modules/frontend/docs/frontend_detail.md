# Frontend — implementation detail

A static, build-free site served directly by FastAPI from `modules/frontend/src`.
No npm, no bundler, no `dist/`. Every page is plain HTML loading ES modules.

## Why no build step

The backend already serves static files, so shipping the frontend as source keeps
deployment to one process and one image. The cost is no JSX and no tree shaking;
at this size neither is worth a toolchain.

## Layout

```
src/
├── *.html              # one file per page
├── css/
│   ├── base.css        # tokens, reset, primitives (buttons, forms, cards…)
│   └── app.css         # app shell, page-specific layouts
└── js/
    ├── api.js          # API client, token storage, refresh, WS ticket
    ├── ui.js           # DOM helpers, formatting, toasts, header, auth guards
    ├── otp.js          # six-box OTP input behaviour
    ├── charts.js       # inline-SVG line chart and bar list
    └── pages/          # one controller per page
```

## Pages

| Page | Purpose |
| :--- | :--- |
| `index.html` | Landing page. The only page with no auth requirement or API calls. |
| `signup.html` | Registration, then hands off to OTP verification. |
| `verify.html` | Six-digit email verification; signs the learner in on success. |
| `login.html` | Sign in. Routes unverified accounts back to verification. |
| `forgot-password.html` / `reset-password.html` | Reset by emailed code. |
| `dashboard.html` | Stats, resume banner, recent lessons, mastery, activity strip. |
| `new-lesson.html` | Upload or pick a document, or type a topic; tune and plan. |
| `classroom.html` | The live lesson: video, curriculum rail, checkpoints, feedback. |
| `report.html` | Score, per-concept timeline, every answer, rewatchable video. |
| `lessons.html` | Searchable, filterable, paginated history. |
| `analytics.html` | Accuracy trend, concept strength, misconceptions, time on task. |
| `settings.html` | Profile, learning preferences, password, devices, deletion. |

## Conventions that matter

**No mock data.** `api.js` throws an `ApiError` when a request fails. Earlier
versions returned invented lesson plans on failure, which made a dead backend
look healthy. Pages render an error state instead.

**Tokens.** The access token lives in `localStorage` and is attached as a Bearer
header. A 401 triggers one transparent refresh-and-retry; concurrent 401s share a
single in-flight refresh so they cannot invalidate each other's rotated token. A
failed refresh clears storage and redirects to login.

**The classroom socket** authenticates with a short-lived ticket from
`POST /lessons/{id}/ticket`, never the access token — URLs leak through logs and
`Referer`.

**Video** is owner-scoped and needs an `Authorization` header, so it cannot go
straight into `<video src>`. It is fetched as a blob and attached as an object
URL, revoked on unload.

**Escaping.** Anything interpolated into an HTML template goes through
`escapeHtml()`. Lesson titles and concepts come from an LLM and from learner
input, so they are never trusted as markup.

**Theming.** Tokens are defined on `:root`, redefined under
`@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`
and again under `:root[data-theme="dark"]`, so the OS preference applies by
default and an explicit choice overrides it.

**Decorative overlays** must carry `pointer-events: none`. A decorative circle on
the dashboard's resume card once sat over the Resume button and swallowed
every click.

## Verified

- 320px to 1920px, light and dark, across every page: no horizontal overflow and
  no console errors.
- Every `a[href]` and enabled `button` is reachable by a click — nothing is
  covered by an overlay.
