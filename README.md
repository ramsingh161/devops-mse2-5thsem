# HealPipe — Self-healing CI/CD pipeline

A small college DevOps project. It deploys a sample Campus API, checks its health,
automatically restores the previous healthy release on failure, reads the failure
logs, and saves an incident ticket with a suggested fix.

## Start in one command

Requires Python 3.10 or newer. No pip packages or paid accounts are required.

```powershell
python server.py
```

Open **http://127.0.0.1:8000**. Keep the terminal running; Ctrl+C stops the server
and its sample app processes. You can also run `./start.ps1` on Windows.

## Two-minute demonstration

1. Startup deploys a healthy baseline. Click **Check live service** to see its version.
2. Select **Missing database configuration**, then **Deploy release**.
3. The candidate returns HTTP 503. The pipeline restores the previous route and
   verifies that the previous release is healthy.
4. Read the recovery timeline, suggested fix, incident ticket, and actual logs.
5. Check the live service again: its version is the same as the healthy baseline.
6. Deploy a **Healthy release**. Its version becomes the active version.

The scenarios deliberately make the app return an unhealthy response. The
"Startup validation error" scenario represents a startup error through HTTP 503;
it does not kill the process. The project also handles actual launch exceptions.

## How it works

```text
Dashboard / GitHub Actions
          |
     Launch candidate ----> Route /service to candidate
                                    |
                               GET /health
                              /           \
                            200           failure
                             |               |
                       Keep release    Restore previous route
                                             |
                                      Verify old health
                                             |
                                   Diagnose logs -> Save ticket
```

This uses a simple blue/green approach: the previous process stays available
while the new release is checked. Rollback changes which process `/service`
routes to, then removes the failed candidate. This makes recovery real and
easy to demonstrate without Kubernetes or a cloud server.

## The few files you need to understand

| File | Purpose |
|---|---|
| `server.py` | HTTP API, deployment, health checks, rollback, SQLite, LLM and tickets |
| `dashboard.html` | Plain HTML, CSS, JavaScript dashboard |
| `sample_app/app.py` | Small application with healthy and broken scenarios |
| `sample_app/Dockerfile` | Container image for the sample application |
| `test_pipeline.py` | Tests that launch real processes and verify recovery |
| `.github/workflows/pipeline.yml` | Automated tests and a Docker deployment/recovery demo |

The remaining files are small configuration helpers. Generated logs and the
SQLite database live in `data/`, which is ignored by Git. History survives
restarts; live processes do not. Each new server session creates a fresh baseline.

## Real LLM diagnosis (optional, needed to demonstrate the AI requirement)

Copy `.env.example` to `.env`. Set your own `OPENAI_API_KEY`; keep it private.
The default model is `gpt-4.1-mini`; change `OPENAI_MODEL` if needed. Restart
the server after changing `.env`. API calls can cost money.

Without a key, **local rules** generate the diagnosis and the UI labels that
explicitly. With a working key, the backend sends redacted demo logs to the
OpenAI Responses API and labels the result **OpenAI LLM**. If the request fails,
local diagnosis still works. Rollback happens before diagnosis, so recovery
does not depend on AI availability. The LLM only suggests fixes; it never
executes generated code.

## GitHub and CI/CD

Create an empty GitHub repository, upload these files including `.github/`,
and push to `main` or `master`. The Actions workflow runs the tests, builds the
Docker image, deploys a healthy baseline and a broken container, verifies
rollback, and uploads the incident database and logs as an artifact.

This deploys on the temporary Actions runner as a demonstration. It does not
leave a publicly hosted application running after the job ends. Local
dashboard history and Actions-runner history are separate databases.

To also create real GitHub incident issues from your local demo, enable
Issues on the repository, create a fine-grained token with **Issues: Read and
write**, and set these values in your private `.env`:

```dotenv
GITHUB_REPOSITORY=your-username/your-repo
GITHUB_TOKEN=your-private-token
CREATE_GITHUB_ISSUES=true
```

This opts into posting one real issue per failed deployment. The default
always saves a local incident ticket and does not contact GitHub. A ticket
with a suggested fix satisfies the assignment's “PR/ticket” option.
Do not put tokens in code, screenshots, Git, or chat.

## Docker mode

Docker CLI is installed on this computer, but Docker Desktop's engine was
not running during initial setup. Open Docker Desktop and wait until it is
ready, then run:

```powershell
python server.py --runtime docker
```

The dashboard stays on the host and manages sample-app containers. To run
the automated container demonstration without a dashboard:

```powershell
python server.py --runtime docker --demo
```

## Verify locally

```powershell
python -m unittest -v
python server.py --demo
```

Tests cover healthy replacement, both failure scenarios, verified rollback,
failure with no baseline, launch errors, concurrent deployment rejection,
persistent incidents, secret redaction, and LLM outage fallback.

## What you need to do yourself

- Run the dashboard and practice the demonstration above.
- Start Docker Desktop to demonstrate container mode.
- Create/sign into your GitHub account and choose the repository to publish.
- Add your own private API key to `.env` for the live LLM demonstration.
- Enable GitHub issue creation only if you want real issues in your repository.

## Viva explanation

**CI** means checking each code change automatically. Our GitHub workflow
runs tests and builds a container. **CD** means deploying a release; our
workflow demonstrates this on its runner. A **health check** asks whether
the application is working. **Rollback** restores traffic to the previous
working release. **Self-healing** means detecting failure and recovering
automatically. **SQLite** stores the history and incident tickets. The
**LLM** helps explain the logs after deterministic recovery.

Scope: this is a local/CI deployment lab, not a production platform. It checks
deployments when they happen; it does not continuously monitor later crashes.
The dashboard binds to localhost and has no login. Keep it local. The recovery
window may briefly return a failed response while the candidate is checked.

Official references: [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[GitHub Issues API](https://docs.github.com/en/rest/issues/issues#create-an-issue),
[OpenAI Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create),
[Docker getting started](https://docs.docker.com/get-started/).
