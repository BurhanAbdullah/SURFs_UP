# PythonAnywhere deployment notes

These notes assume the PythonAnywhere account uses:

- user: `mathewjowens`
- virtualenv: `/home/mathewjowens/.virtualenvs/surfs-up`
- SURF checkout: `/home/mathewjowens/SURF`
- SURFs_UP checkout: `/home/mathewjowens/SURFs_UP`

## One-time clone/install

Use the `dev` branch of `SURF` and the main branch of `SURFs_UP`.

```bash
cd /home/mathewjowens

git clone --branch dev --single-branch https://github.com/University-of-Reading-Space-Science/SURF.git SURF
git clone https://github.com/University-of-Reading-Space-Science/SURFs_UP.git SURFs_UP

workon surfs-up
python -m pip install --upgrade pip setuptools wheel

cd /home/mathewjowens/SURF
pip install --no-cache-dir -e .

cd /home/mathewjowens/SURFs_UP
pip install --no-cache-dir -e .
```

## PythonAnywhere web app settings

Set:

```text
Source code:       /home/mathewjowens/SURFs_UP
Working directory: /home/mathewjowens/SURFs_UP
Virtualenv:        /home/mathewjowens/.virtualenvs/surfs-up
```

The WSGI file should contain:

```python
import sys

project = "/home/mathewjowens/SURFs_UP"
if project not in sys.path:
    sys.path.insert(0, project)

from wsgi import application
```

Reload the web app after installs or pulls.

## Always-on simulation worker

On the **Tasks** page, create one Always-on Task with:

```bash
/home/mathewjowens/.virtualenvs/surfs-up/bin/surfs-up-worker
```

The worker and web app share persistent job and result files under
`/home/mathewjowens/.cache/surfs_up`. The web request only enqueues a run, so
simulations are not subject to PythonAnywhere's five-minute web-request limit.
Use exactly one worker to avoid running multiple memory-intensive SURF models
at once. Only the newest completed model pickle is retained; superseded models
and abandoned temporary pickle writes are pruned at web/worker startup and
after each background job.

## Routine update workflow

On your local machine, commit and push changes in whichever repo changed.

On PythonAnywhere:

```bash
workon surfs-up

cd /home/mathewjowens/SURF
git pull
pip install -e .

cd /home/mathewjowens/SURFs_UP
git pull
pip install -e .
```

Then reload the web app and restart the Always-on Task so it uses the updated
worker code.

Editable installs mean a plain `git pull` plus web reload is often enough for Python/template changes, but rerunning `pip install -e ...` is a low-faff habit that also catches dependency and package-metadata changes.

## Quick checks

```bash
workon surfs-up

cd /home/mathewjowens/SURF
git branch --show-current
python -c "import surf; print(surf.__file__)"

cd /home/mathewjowens/SURFs_UP
git log --oneline -2
grep -n "_RUN_CACHE_DIR" surfs_up/web/app.py
python -c "from wsgi import application; print(application.url_map)"
```

Expected:

- `SURF` branch is `dev`.
- `import surf` points into `/home/mathewjowens/SURF/surf/...`, not only site-packages.
- `SURFs_UP` includes the run-cache fix (`_RUN_CACHE_DIR`) so plots/movies survive worker changes.
- The Always-on Task shows as running, and its log reports no import errors.

## Troubleshooting reminders

- If runs remain at “Queued for processing”, check the Always-on Task status and
  log, then restart it.
- A worker restart requeues any job that it had claimed but not completed.
- Missing `zeep`, `cdflib`, or `mpl_animators` means SunPy extras were not installed. `SURFs_UP` depends on `sunpy[net,timeseries,visualization]`, so reinstall with `pip install -e .`.
- The Flask/Dash conflict warning from system packages is not relevant to this Flask app.
