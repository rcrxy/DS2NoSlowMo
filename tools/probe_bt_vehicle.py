"""Read-only capture of the BT encounter state consumed by vehicle code."""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import time

from probe_timescale import (EXPECTED_SHA256, MODULEENTRY32W, Memory,
                             enumerate_entries, k32)


STATE_SLOT_RVA = 0x623F9D8  # Loaded at 0x1F80702; allocation size is 0x20.
RESOURCE_SLOT_RVA = 0xA1D5CE0  # Loaded at 0x1EC9899.
PREFIXES = {
    0x1F806F0: bytes.fromhex('c5fa114c2410534883ec4080793c0048'),
    0x1EC9890: bytes.fromhex('40574881ec800000004c8b0540c43008'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--watch', type=float, default=0)
    parser.add_argument('--interval', type=float, default=0.01)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 0 <= args.watch <= 300 or not 0.005 <= args.interval <= 1:
        parser.error('Watch must be 0..300 seconds; interval must be 0.005..1 second.')
    modules = list(enumerate_entries(8, args.pid, MODULEENTRY32W,
                                    k32.Module32FirstW, k32.Module32NextW))
    module, = [m for m in modules if m.szModule == 'DS2.exe']
    digest = hashlib.sha256(Path(module.szExePath).read_bytes()).hexdigest().upper()
    if digest != EXPECTED_SHA256:
        raise RuntimeError('Executable SHA256 differs from the analyzed version.')
    base = module.modBaseAddr
    memory = Memory(args.pid)
    try:
        for rva, expected in PREFIXES.items():
            if memory.read(base + rva, len(expected)) != expected:
                raise RuntimeError(f'Code differs at RVA {rva:#x}.')
        state = memory.pointer(base + STATE_SLOT_RVA)
        resource = memory.pointer(base + RESOURCE_SLOT_RVA)
        if not state or not resource:
            raise RuntimeError('Encounter state or resource is null.')
        resource_raw = memory.read(resource, 0x68)
        if struct.unpack_from('<Q', resource_raw)[0] != base + 0x33A63F8:
            raise RuntimeError('DSGazerAreaEnterResource constructor vtable does not match.')
        if memory.pointer(base + 0x33A63F8) != base + 0x1EC29E0:
            raise RuntimeError('DSGazerAreaEnterResource RTTI getter does not match.')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('w', encoding='utf-8') as output:
            header = {'record_kind': 'header', 'pid': args.pid, 'base': hex(base),
                      'exe_sha256': digest, 'state_address': hex(state),
                      'resource_address': hex(resource), 'resource_raw_bytes': resource_raw.hex(),
                      'resource_floats': {name: struct.unpack_from('<f', resource_raw, off)[0]
                                          for name, off in [('OffTime', 0x50),
                                                            ('StartChillsTimeFromOff', 0x54),
                                                            ('EndChillsTimeFromOff', 0x58)]}}
            output.write(json.dumps(header) + '\n')
            output.flush()
            print(json.dumps(header), flush=True)
            print('Capture started.', flush=True)
            start = time.monotonic()
            count = 0
            errors = 0
            while True:
                elapsed = time.monotonic() - start
                record = {'record_kind': 'sample', 'elapsed': elapsed,
                          'local_time': datetime.now().isoformat(timespec='milliseconds')}
                try:
                    if memory.pointer(base + STATE_SLOT_RVA) != state:
                        raise RuntimeError('Encounter state pointer changed.')
                    raw = memory.read(state, 0x20)
                    record.update(raw_bytes=raw.hex(),
                                  floats_by_offset={hex(o): struct.unpack_from('<f', raw, o)[0]
                                                    for o in [0, 4, 0x10]},
                                  integers_by_offset={hex(o): struct.unpack_from('<i', raw, o)[0]
                                                      for o in [8, 0xC, 0x14, 0x18]},
                                  bytes_by_offset={hex(o): raw[o] for o in [0x1C, 0x1D, 0x1E]})
                except (OSError, RuntimeError) as error:
                    errors += 1
                    record['read_error'] = str(error)
                output.write(json.dumps(record) + '\n')
                count += 1
                if args.watch == 0 or elapsed >= args.watch:
                    break
                time.sleep(args.interval)
            output.write(json.dumps({'record_kind': 'summary', 'samples': count,
                                     'read_errors': errors}) + '\n')
            print(f'Finished: {count} samples, {errors} read errors.', flush=True)
    finally:
        memory.close()


if __name__ == '__main__':
    main()
