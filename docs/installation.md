# Installing AccessMatrix

This guide explains how to install and run AccessMatrix from source.

AccessMatrix v0.1.0 is a local-first API authorization regression testing platform. The current release requires Python 3.13.

---

## Requirements

Before installing AccessMatrix, make sure the following are available:

- Git
- Python 3.13
- uv
- a modern web browser

For normal use, Node.js is **not required**.

Node.js is only needed if you intend to modify and rebuild the React frontend.

---

## Python Version

AccessMatrix v0.1.0 requires:

```text
Python >=3.13,<3.14
```

Your system can have other Python versions installed.

AccessMatrix uses the Python environment managed by `uv`, so the globally installed Python version does not need to be changed as long as uv creates the project environment using Python 3.13.

To check the Python version inside the AccessMatrix environment:

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe --version
```

### Linux / macOS

```bash
./.venv/bin/python --version
```

Expected:

```text
Python 3.13.x
```

---

# 1. Install Git

Verify Git is available:

```bash
git --version
```

If the command is unavailable, install Git using the package manager or installer appropriate for your operating system.

---

# 2. Install Python 3.13

AccessMatrix currently supports Python 3.13.

Verify your available Python installation:

```bash
python --version
```

The default system Python does not necessarily have to be Python 3.13 because uv can manage the project environment separately.

---

# 3. Install uv

AccessMatrix uses `uv` for dependency and Python environment management.

Official uv installation instructions:

https://docs.astral.sh/uv/getting-started/installation/

After installation, verify:

```bash
uv --version
```

---

# 4. Clone AccessMatrix

Clone the repository:

```bash
git clone https://github.com/ubaidahmadbhat/accessmatrix.git
```

Then enter the project directory:

```bash
cd accessmatrix
```

The final GitHub repository URL will replace the placeholder before the v0.1.0 public release.

---

# 5. Install Dependencies

From the AccessMatrix directory:

```bash
uv sync
```

uv will:

- create the local Python virtual environment
- select a compatible Python version
- install AccessMatrix
- install the required Python dependencies

The environment is normally created under:

```text
.venv/
```

---

# 6. Start AccessMatrix

Run:

```bash
uv run accessmatrix gui
```

The local AccessMatrix application will start.

Open:

```text
http://127.0.0.1:8765
```

in your browser.

---

# Windows Installation Example

A typical Windows PowerShell workflow is:

```powershell
git clone https://github.com/ubaidahmadbhat/accessmatrix.git

Set-Location .\accessmatrix

uv sync

uv run accessmatrix gui
```

Then open:

```text
http://127.0.0.1:8765
```

---

# Linux Installation Example

```bash
git clone https://github.com/ubaidahmadbhat/accessmatrix.git

cd accessmatrix

uv sync

uv run accessmatrix gui
```

Then open:

```text
http://127.0.0.1:8765
```

---

# macOS Installation Example

```bash
git clone https://github.com/ubaidahmadbhat/accessmatrix.git

cd accessmatrix

uv sync

uv run accessmatrix gui
```

Then open:

```text
http://127.0.0.1:8765
```

---

# What Gets Installed?

The Python application includes:

- FastAPI backend
- AccessMatrix CLI
- authorization-testing engine
- BOLA scanning engine
- findings storage
- report generation
- security and execution controls
- local settings
- audit support
- bundled production GUI assets

For normal users, the frontend does not need to be built separately.

---

# Frontend Development

Developers modifying the React GUI work in:

```text
gui/
```

Node.js and npm are required only for frontend development.

Typical workflow:

```bash
cd gui

npm install

npm run build
```

The frontend source is separate from the production GUI assets bundled with the Python application.

Normal users should not need to run these commands.

---

# Starting the Bundled Demo

AccessMatrix includes a deliberately vulnerable local invoice API for learning and testing.

Open a separate terminal from the project directory:

```bash
uv run uvicorn accessmatrix.demo_api.app:app --host 127.0.0.1 --port 9000
```

The demo API will run at:

```text
http://127.0.0.1:9000
```

Keep that terminal running while using the demo.

The complete walkthrough is available in:

```text
docs/demo-guide.md
```

---

# Demo Credentials

The bundled demo uses intentionally fake credentials.

### Windows PowerShell

```powershell
$env:ACCESSMATRIX_ALICE_TOKEN = "demo-alice-token"
$env:ACCESSMATRIX_BOB_TOKEN = "demo-bob-token"
$env:ACCESSMATRIX_ADMIN_TOKEN = "demo-admin-token"

uv run accessmatrix gui
```

### Linux / macOS

```bash
export ACCESSMATRIX_ALICE_TOKEN="demo-alice-token"
export ACCESSMATRIX_BOB_TOKEN="demo-bob-token"
export ACCESSMATRIX_ADMIN_TOKEN="demo-admin-token"

uv run accessmatrix gui
```

These values exist only for the local demonstration environment.

Never store real credentials in source code or Git.

---

# Stopping AccessMatrix

Return to the terminal running AccessMatrix and press:

```text
Ctrl+C
```

If the demo API is also running, stop it separately in its own terminal.

---

# Updating AccessMatrix

After future versions are published:

```bash
git pull
uv sync
```

Then restart AccessMatrix.

---

# Windows File-Lock Note

On Windows, an actively running AccessMatrix process may lock:

```text
.venv\Scripts\accessmatrix.exe
```

If `uv sync` or `uv run` attempts to rebuild AccessMatrix while the application is already running, Windows may display an error similar to:

```text
The process cannot access the file because it is being used by another process.
```

This does not normally indicate corrupted installation data.

Stop the currently running AccessMatrix process, then run:

```powershell
uv sync
```

and start AccessMatrix again.

---

# Common Installation Problems

## `uv` is not recognized

Confirm uv is installed and available on your `PATH`.

Opening a new terminal after installation may be necessary.

---

## Wrong Python version

Check the project environment directly.

### Windows

```powershell
.\.venv\Scripts\python.exe --version
```

### Linux / macOS

```bash
./.venv/bin/python --version
```

AccessMatrix v0.1.0 expects Python 3.13.

---

## Port 8765 is already in use

Another application may already be using the AccessMatrix GUI port.

Identify and stop the conflicting application before starting AccessMatrix.

---

## Port 9000 is already in use

Port 9000 is used by the bundled demo API.

The main AccessMatrix application does not require the demo API for normal use.

---

## AccessMatrix starts but the browser does not open automatically

Open:

```text
http://127.0.0.1:8765
```

manually.

---

# Security Guidance

Do not store real authentication secrets inside the repository.

Credentials used with real APIs should be managed using supported mechanisms such as:

- environment variables
- operating-system credential stores
- supported keyring references

Also protect locally generated:

- findings
- scan evidence
- reports
- authorization datasets
- OpenAPI specifications
- audit records

These may contain sensitive security information.

See:

```text
docs/security-model.md
```

for the complete security model.

---

# Next Step

After installation, continue with:

```text
docs/getting-started.md
```

That guide explains how AccessMatrix works and walks through the complete first assessment workflow.
