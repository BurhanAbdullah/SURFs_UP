# SURFs_UP

SURFs_UP provides a web interface for
[SURF](https://github.com/University-of-Reading-Space-Science/SURF). It can be
run locally or deployed to a WSGI host such as PythonAnywhere.

The Flask application uses `surfs_up.core` for request validation, code
generation, plotting, and execution.

## Development installation

Install SURF and SURFs_UP into the same environment:

```powershell
pip install -e ../SURF
pip install -e .
```

Run the local web application with either command:

```powershell
surfs-up
surfs-up-web
```

The Flask workflow supports user-specified, MAS, WSA, CorTom, OMNI-backmapped,
and OMNI-outwards ambient boundaries, plus magnetic boundaries, streak lines,
and JSON-defined Cone CMEs.

Open `http://127.0.0.1:5000`. Start the background worker in a second terminal:

```powershell
surfs-up-worker
```

The web form queues model runs and polls their persistent status. Completed
models can produce 2D maps, radial profiles, time series, and downloadable MP4
movies. Job state and the newest completed model are stored under
`~/.cache/surfs_up` by default, so web-worker reloads do not lose the current
run. Older model pickles and abandoned partial writes are removed at startup
and after jobs.

## PythonAnywhere

Create a virtual environment, install SURF and then install this project.
Configure the PythonAnywhere web app's WSGI file to import the
provided application:

```python
import sys

project = "/home/YOUR_USERNAME/SURFs_UP"
if project not in sys.path:
    sys.path.insert(0, project)

from wsgi import application
```

Set the web app source directory to the repository and reload it. The repository
root [wsgi.py](wsgi.py) is intentionally small so deployment-specific settings
can later be supplied without coupling them to Flask routes.

On the PythonAnywhere **Tasks** page, add an Always-on Task using the worker
installed in the same virtual environment as the web app:

```bash
/home/YOUR_USERNAME/.virtualenvs/YOUR_ENV/bin/surfs-up-worker
```

Only run one SURFs_UP worker. Its queue keeps long simulations outside the
five-minute web-request limit, reports progress to the browser, and requeues a
job if the worker is restarted while processing it.

Both processes must use the same home directory. You can override the storage
locations in both the WSGI environment and Always-on Task environment with
`SURFS_UP_JOB_DIR` and `SURFS_UP_RUN_CACHE_DIR`.
