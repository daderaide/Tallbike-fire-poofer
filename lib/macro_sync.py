# macro_sync.py — Push macros from control box to relay box
# Uses config sync registers 200-232 defined in PROTOCOL.md

import json
from macro_store import list_macros, load

_sync_needed = False

def request_sync():
    """Flag that macros need to be pushed to relay box."""
    global _sync_needed
    _sync_needed = True

def sync_pending():
    """Check if a sync is pending."""
    return _sync_needed

def do_sync(host, slave_addr):
    """Send all macros to relay box. Call from comms_task.
    Returns True on success, False on error."""
    global _sync_needed
    _sync_needed = False

    # Build payload: {"macros": {"name": {...}, ...}}
    payload = {"macros": {}}
    for name in list_macros():
        try:
            payload["macros"][name] = load(name)
        except:
            pass

    data = json.dumps(payload).encode('utf-8')
    total_len = len(data)
    checksum = sum(data) & 0xFFFF

    # Send in 60-byte chunks (30 data registers × 2 bytes each)
    chunk_size = 60
    offset = 0

    while offset < total_len:
        chunk = data[offset:offset + chunk_size]

        # Pad last chunk to 60 bytes
        if len(chunk) < chunk_size:
            chunk = chunk + b'\x00' * (chunk_size - len(chunk))

        # Build register values: [length, offset, data0, data1, ..., data29]
        regs = [total_len, offset]
        for i in range(30):
            regs.append((chunk[i * 2] << 8) | chunk[i * 2 + 1])

        # Write registers 200-231 atomically
        try:
            host.write_multiple_registers(
                slave_addr=slave_addr,
                starting_address=200,
                register_values=regs,
                signed=False
            )
        except:
            return False

        offset += chunk_size

    # Write checksum to signal completion
    try:
        host.write_single_register(
            slave_addr=slave_addr,
            register_address=232,
            register_value=checksum,
            signed=False
        )
    except:
        return False

    return True