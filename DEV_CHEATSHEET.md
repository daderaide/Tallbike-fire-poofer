# FUPA Dev Cheat Sheet

## Makefile Targets

| Command | What it does |
|---|---|
| `make upload` | Deploy code to both boards, keeps main.py running |
| `make dev-control` | Upload + REPL on control box (disables main.py) |
| `make dev-relay` | Upload + REPL on relay box (disables main.py) |
| `make dev-restore-control` | Re-enables main.py on control box |
| `make dev-restore-relay` | Re-enables main.py on relay box |

## REPL Keys

| Keys | What it does |
|---|---|
| **Ctrl+E** | Enter paste mode (you'll see `===`) |
| **Ctrl+D** | Execute pasted code / soft reset if at `>>>` |
| **Ctrl+C** | Stop running code |
| **Ctrl+]** | Exit mpremote entirely |

## Typical Dev Session

1. `make dev-control` → uploads code, lands in REPL
2. **Ctrl+E**, paste test code, **Ctrl+D** to run
3. Iterate — **Ctrl+E**, paste again, **Ctrl+D**
4. **Ctrl+]** to exit mpremote
5. `make dev-restore-control` when done

## Serial Ports

| Board | Port |
|---|---|
| Control box | `/dev/tty.usbserial-110` |
| Relay box | `/dev/tty.usbserial-10` |

## Quick REPL Commands

```python
# Check what's on the board
import os
os.listdir('/')
os.listdir('/lib')

# Check if main.py is disabled
os.listdir('/')  # look for _main.py

# Manual reset
import machine
machine.reset()
```