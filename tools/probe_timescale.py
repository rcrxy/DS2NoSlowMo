"""Read-only DS2 1.10.89.0 time-control snapshot. No injection or memory writes."""

import argparse
import ctypes as ct
from ctypes import wintypes as wt
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import time

if os.name != "nt" or ct.sizeof(ct.c_void_p) != 8:
    raise SystemExit("Run with 64-bit Python on Windows.")

EXPECTED_SHA256 = "BF3D1C665545930BC850D8F5DF486F7395885BB729D4FD408FDB03390DE0765B"
CONTROL_SLOT_RVA = 0x623E9A8
WORLD_SLOT_RVA = 0x623E338
PARAMETER_GET_RTTI_RVA = 0xD708E0
ENTRY_PREFIXES = {
    0x724530: bytes.fromhex("488b05019eb1054885c0741d488b88d0"),
    0x7237E0: bytes.fromhex("488bc45341564881eca8000000c5fa10"),
    0x724010: bytes.fromhex("488bc4534881eca00000004889680848"),
    0xD70E80: bytes.fromhex("48895c240848897c241055488d6c24b1"),
    0xD712D0: bytes.fromhex("488bc4554155488d68a14881ecf80000"),
    0xD71E60: bytes.fromhex("488bc448895818555657415441554156"),
}


class PROCESSENTRY32W(ct.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ct.c_size_t), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", wt.LONG), ("dwFlags", wt.DWORD), ("szExeFile", wt.WCHAR * 260),
    ]


class MODULEENTRY32W(ct.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD),
        ("modBaseAddr", ct.c_void_p), ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE),
        ("szModule", wt.WCHAR * 256), ("szExePath", wt.WCHAR * 260),
    ]


assert ct.sizeof(PROCESSENTRY32W) == 568
assert ct.sizeof(MODULEENTRY32W) == 1080
k32 = ct.WinDLL("KERNEL32.dll", use_last_error=True)
k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.CloseHandle.restype = wt.BOOL
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ct.c_void_p, ct.c_void_p, ct.c_size_t, ct.POINTER(ct.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
for name, entry in [("Process32FirstW", PROCESSENTRY32W), ("Process32NextW", PROCESSENTRY32W),
                    ("Module32FirstW", MODULEENTRY32W), ("Module32NextW", MODULEENTRY32W)]:
    function = getattr(k32, name)
    function.argtypes = [wt.HANDLE, ct.POINTER(entry)]
    function.restype = wt.BOOL


def enumerate_entries(flags, pid, entry_type, first, next_entry):
    snapshot = k32.CreateToolhelp32Snapshot(flags, pid)
    if snapshot == ct.c_void_p(-1).value:
        raise ct.WinError(ct.get_last_error())
    try:
        entry = entry_type()
        entry.dwSize = ct.sizeof(entry)
        available = first(snapshot, ct.byref(entry))
        while available:
            yield entry_type.from_buffer_copy(entry)
            available = next_entry(snapshot, ct.byref(entry))
        if ct.get_last_error() != 18:  # ERROR_NO_MORE_FILES
            raise ct.WinError(ct.get_last_error())
    finally:
        k32.CloseHandle(snapshot)


class Memory:
    def __init__(self, pid):
        # PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION; no write rights.
        self.handle = k32.OpenProcess(0x0010 | 0x1000, False, pid)
        if not self.handle:
            raise ct.WinError(ct.get_last_error())

    def close(self):
        k32.CloseHandle(self.handle)

    def read(self, address, size):
        buffer = ct.create_string_buffer(size)
        read = ct.c_size_t()
        if not k32.ReadProcessMemory(self.handle, address, buffer, size, ct.byref(read)):
            raise ct.WinError(ct.get_last_error())
        if read.value != size:
            raise RuntimeError(f"Partial read at {address:#x}: {read.value}/{size}")
        return buffer.raw

    def pointer(self, address):
        return struct.unpack("<Q", self.read(address, 8))[0]


def finite(value):
    return value if math.isfinite(value) else repr(value)


def slow_manager_snapshot(memory, base):
    # Exact chain used by the registered IsGameInSlowMotion function at RVA 0x724530.
    world = memory.pointer(base + WORLD_SLOT_RVA)
    if not world:
        raise RuntimeError("World pointer used by IsGameInSlowMotion is null.")
    manager = memory.pointer(world + 0x5D0)
    if not manager:
        raise RuntimeError("Slow-motion manager pointer is null.")
    header = memory.read(manager + 0x10, 0x18)
    count, capacity, entries = struct.unpack_from("<iiQ", header)
    if not 0 <= count <= capacity <= 4096:
        raise RuntimeError("Slow-motion manager array exceeds the read budget.")
    raw = memory.read(entries, count * 0x1C) if count else b""
    active = []
    for index in range(count):
        offset = index * 0x1C
        active.append({
            "id_value_at_0x0": struct.unpack_from("<i", raw, offset)[0],
            "floats_by_offset": {hex(o): finite(struct.unpack_from("<f", raw, offset + o)[0])
                                 for o in [4, 8, 0xC, 0x10, 0x14, 0x18]},
        })
    if header[:16] != memory.read(manager + 0x10, 16):
        raise RuntimeError("Slow-motion manager array changed during this sample.")
    if memory.pointer(base + WORLD_SLOT_RVA) != world or memory.pointer(world + 0x5D0) != manager:
        raise RuntimeError("Slow-motion manager pointer changed during this sample.")
    outputs = memory.read(world + 0x1D8, 8)
    return {
        "world_address": hex(world), "manager_address": hex(manager),
        "manager_floats_by_offset": {hex(o): finite(struct.unpack_from("<f", header, o - 0x10)[0])
                                    for o in [0x20, 0x24]},
        "world_floats_by_offset": {hex(o): finite(struct.unpack_from("<f", outputs, o - 0x1D8)[0])
                                  for o in [0x1D8, 0x1DC]},
        "active_entries": active,
    }


def curve_snapshot(memory, base, pointer):
    vtable = memory.pointer(pointer)
    if memory.pointer(vtable) != base + 0x1B30D90:
        raise RuntimeError(f"CurveResource type not confirmed at {pointer:#x}.")
    header = memory.read(pointer + 0x20, 0x20)
    count, capacity, entries = struct.unpack_from("<iiQ", header)
    if not 0 < count <= capacity <= 4096:
        raise RuntimeError("CurvePoints array exceeds the read budget or is empty.")
    data = memory.read(entries, count * 0x18)
    points = []
    for index in range(count):
        values = struct.unpack_from("<6f", data, index * 0x18)
        points.append({"Position": {"X": finite(values[0]), "Y": finite(values[1])},
                       **{name: finite(value) for name, value in zip(
                           ["InTangent", "OutTangent", "InTangentX", "OutTangentX"], values[2:])}})
    if header[:16] != memory.read(pointer + 0x20, 16):
        raise RuntimeError("CurvePoints array changed during the snapshot.")
    return {"address": hex(pointer), "CurvePoints": points,
            "CurveEvaluationType": header[0x10], "PreInfinity": header[0x11], "PostInfinity": header[0x12],
            "HighestPoint": finite(struct.unpack_from("<f", header, 0x14)[0]),
            "LowestPoint": finite(struct.unpack_from("<f", header, 0x18)[0])}


def snapshot(pid, parameter_hash=None):
    modules = list(enumerate_entries(0x00000008, pid, MODULEENTRY32W,
                                   k32.Module32FirstW, k32.Module32NextW))
    main = [m for m in modules if m.szModule == "DS2.exe"]
    if len(main) != 1:
        raise RuntimeError("Expected exactly one module named DS2.exe.")
    module = main[0]
    game_path = Path(module.szExePath)
    digest = hashlib.sha256(game_path.read_bytes()).hexdigest().upper()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"Unsupported executable SHA256: {digest}")
    base = module.modBaseAddr
    memory = Memory(pid)
    try:
        for rva, expected in ENTRY_PREFIXES.items():
            if memory.read(base + rva, len(expected)) != expected:
                raise RuntimeError(f"Runtime code differs at DS2.exe+{rva:#x}; refusing this layout.")
        controller = memory.pointer(base + CONTROL_SLOT_RVA)
        if controller == 0:
            raise RuntimeError("Time-control object is not initialized yet.")
        header = memory.read(controller, 0x58)
        parameter_count = struct.unpack_from("<i", header, 0x18)[0]
        parameter_entries = struct.unpack_from("<Q", header, 0x20)[0]
        active_count = struct.unpack_from("<i", header, 0x28)[0]
        active_entries = struct.unpack_from("<Q", header, 0x30)[0]
        # Defensive read budgets, not claims about the game's actual limits.
        if not 0 <= parameter_count <= 4096 or not 0 <= active_count <= 256:
            raise RuntimeError(f"Array counts exceed read budgets: {parameter_count}, {active_count}")
        pointers = struct.unpack(f"<{parameter_count}Q", memory.read(parameter_entries, parameter_count * 8)) if parameter_count else ()
        parameters = []
        for pointer in pointers:
            data = memory.read(pointer, 0x70)
            vtable = struct.unpack_from("<Q", data)[0]
            getter = memory.pointer(vtable)
            if getter != base + PARAMETER_GET_RTTI_RVA:
                raise RuntimeError(f"Parameter type not confirmed at {pointer:#x}; getter={getter:#x}")
            record = {"address": hex(pointer), "Name": hex(struct.unpack_from("<I", data, 0x20)[0])}
            for name, offset in [("TimeScale", 0x24), ("PlayerTimeScale", 0x28), ("CameraTimeScale", 0x2C),
                                 ("TimeDuration", 0x30), ("TransitionTime", 0x34), ("RemoveTransitionTime", 0x38)]:
                record[name] = finite(struct.unpack_from("<f", data, offset)[0])
            record["Priority"] = struct.unpack_from("<I", data, 0x60)[0]
            for name, offset in [("DisableCancelByCancelAllFunction", 0x64),
                                 ("IsForEnemyDefeatedWithCloseCombat", 0x65),
                                 ("IsForEnemyDefeatedWithFarCombat", 0x66), ("NeedBlurEffect", 0x67), ("IsShortSlow", 0x68)]:
                record[name] = data[offset]
            for name, offset in [("TimeScaleCurve", 0x40), ("PlayerTimeScaleCurve", 0x48), ("CameraTimeScaleCurve", 0x50)]:
                record[name] = hex(struct.unpack_from("<Q", data, offset)[0])
            if parameter_hash is not None and int(record["Name"], 16) == parameter_hash:
                record["curve_details"] = {name: curve_snapshot(memory, base, int(record[name], 16))
                    for name in ["TimeScaleCurve", "PlayerTimeScaleCurve", "CameraTimeScaleCurve"]
                    if int(record[name], 16)}
            parameters.append(record)
        if parameter_hash is not None and not any(int(p["Name"], 16) == parameter_hash for p in parameters):
            raise RuntimeError(f"Parameter Name hash not present: {parameter_hash:#x}.")
        active = []
        for index in range(active_count):
            address = active_entries + index * 0x88
            data = memory.read(address, 0x88)
            active.append({
                "address": hex(address), "Name_value_at_0x60": hex(struct.unpack_from("<I", data, 0x60)[0]),
                "id_value_at_0x64": struct.unpack_from("<I", data, 0x64)[0],
                "raw_bytes": data.hex(),
                "curve_references_by_offset": {hex(o): hex(struct.unpack_from("<Q", data, o)[0])
                                               for o in [0x40, 0x48, 0x50]},
                "floats_by_offset": {hex(o): finite(struct.unpack_from("<f", data, o)[0]) for o in
                    [0, 4, 8, 0xC, 0x10, 0x28, 0x2C, 0x70, 0x74, 0x78, 0x7C, 0x80]},
            })
        after = memory.read(controller, 0x38)
        if header[0x18:0x38] != after[0x18:0x38] or memory.pointer(base + CONTROL_SLOT_RVA) != controller:
            raise RuntimeError("Controller arrays changed during the snapshot; collect again.")
        return {
            "local_time": datetime.now().astimezone().isoformat(), "pid": pid,
            "module_path": str(game_path), "module_base": hex(base), "sha256": digest,
            "controller_slot": hex(base + CONTROL_SLOT_RVA), "controller": hex(controller),
            "controller_floats_by_offset": {hex(o): finite(struct.unpack_from("<f", header, o)[0]) for o in
                [0x40, 0x44, 0x48, 0x4C, 0x50, 0x54]},
            "parameters": parameters, "active_entries": active,
            "slow_motion_manager": slow_manager_snapshot(memory, base),
            "note": "Read-only sequential snapshot; float values are not an atomic capture.",
        }
    finally:
        memory.close()


def watch(pid, output, seconds, interval, capture_active_curves=False):
    baseline = snapshot(pid)
    base = int(baseline["module_base"], 16)
    controller = int(baseline["controller"], 16)
    output.parent.mkdir(parents=True, exist_ok=True)
    memory = Memory(pid)
    count = 0
    errors = 0
    captured_curves = set()
    start = time.perf_counter()
    try:
        with output.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps({"record_kind": "baseline", "data": baseline}, allow_nan=False) + "\n")
            stream.flush()
            print(f"Capture started: PID={pid}, controller={controller:#x}, duration={seconds}s", flush=True)
            deadline = start
            while time.perf_counter() - start < seconds:
                elapsed = time.perf_counter() - start
                try:
                    if memory.pointer(base + CONTROL_SLOT_RVA) != controller:
                        raise RuntimeError("Time-control object changed; stop and take a new baseline.")
                    header = memory.read(controller + 0x28, 0x30)
                    active_count = struct.unpack_from("<i", header)[0]
                    entries = struct.unpack_from("<Q", header, 8)[0]
                    if not 0 <= active_count <= 256:
                        raise RuntimeError("Active array count exceeds the read budget.")
                    data = memory.read(entries, active_count * 0x88) if active_count else b""
                    if header[:16] != memory.read(controller + 0x28, 16):
                        raise RuntimeError("Active array changed during this sample.")
                    active = []
                    for index in range(active_count):
                        raw = data[index * 0x88:(index + 1) * 0x88]
                        active.append({
                            "Name_value_at_0x60": hex(struct.unpack_from("<I", raw, 0x60)[0]),
                            "id_value_at_0x64": struct.unpack_from("<I", raw, 0x64)[0],
                            "raw_bytes": raw.hex(),
                            "curve_references_by_offset": {hex(o): hex(struct.unpack_from("<Q", raw, o)[0])
                                                           for o in [0x40, 0x48, 0x50]},
                            "floats_by_offset": {hex(o): finite(struct.unpack_from("<f", raw, o)[0]) for o in
                                [0, 4, 8, 0xC, 0x10, 0x28, 0x2C, 0x70, 0x74, 0x78, 0x7C, 0x80]},
                        })
                    record = {
                        "record_kind": "sample", "elapsed_seconds": elapsed,
                        "local_time": datetime.now().astimezone().isoformat(),
                        "controller_floats_by_offset": {hex(o): finite(struct.unpack_from("<f", header, o - 0x28)[0])
                            for o in [0x40, 0x44, 0x48, 0x4C, 0x50, 0x54]},
                        "active_entries": active,
                        "slow_motion_manager": slow_manager_snapshot(memory, base),
                    }
                    count += 1
                except (OSError, RuntimeError) as error:
                    errors += 1
                    record = {"record_kind": "read_error", "elapsed_seconds": elapsed, "error": str(error)}
                stream.write(json.dumps(record, allow_nan=False) + "\n")
                if capture_active_curves and record["record_kind"] == "sample":
                    for entry in record["active_entries"]:
                        for offset, address in entry["curve_references_by_offset"].items():
                            pointer = int(address, 16)
                            if not pointer or pointer in captured_curves:
                                continue
                            captured_curves.add(pointer)
                            curve_record = {"record_kind": "active_curve", "elapsed_seconds": elapsed,
                                            "Name_value_at_0x60": entry["Name_value_at_0x60"],
                                            "first_reference_offset": offset, "address": address}
                            try:
                                curve_record["data"] = curve_snapshot(memory, base, pointer)
                            except (OSError, RuntimeError) as error:
                                curve_record["read_error"] = str(error)
                            stream.write(json.dumps(curve_record, allow_nan=False) + "\n")
                if count % 100 == 0:
                    stream.flush()
                deadline += interval
                remaining = deadline - time.perf_counter()
                if remaining > 0:
                    time.sleep(remaining)
                else:
                    deadline = time.perf_counter()
            stream.flush()
    finally:
        memory.close()
    print(f"Capture complete: {count} samples, {errors} read errors; {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--output", type=Path, default=Path("build/analysis/runtime-snapshot.json"))
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--parameter-hash", type=lambda value: int(value, 0),
                        help="Also read the curves of this exact parameter Name hash (snapshot only).")
    parser.add_argument("--watch", type=float, help="Capture for this many real-time seconds.")
    parser.add_argument("--interval", type=float, default=0.01, help="Sampling interval in real-time seconds.")
    parser.add_argument("--capture-active-curves", action="store_true",
                        help="During watch, read each new active curve once after validating CurveResource RTTI.")
    args = parser.parse_args()
    if args.self_test:
        payload = ct.create_string_buffer(b"DS2 read-only probe test")
        memory = Memory(os.getpid())
        try:
            assert memory.read(ct.addressof(payload), ct.sizeof(payload)) == payload.raw
        finally:
            memory.close()
        modules = list(enumerate_entries(0x8, os.getpid(), MODULEENTRY32W, k32.Module32FirstW, k32.Module32NextW))
        assert modules
        print(f"ReadProcessMemory and module enumeration passed; {len(modules)} modules.")
        return
    pid = args.pid
    if pid is None:
        pids = [e.th32ProcessID for e in enumerate_entries(0x2, 0, PROCESSENTRY32W, k32.Process32FirstW, k32.Process32NextW)
                if e.szExeFile == "DS2.exe"]
        if len(pids) != 1:
            raise RuntimeError(f"Expected one running DS2.exe, found {pids}. Start the game or supply --pid.")
        pid = pids[0]
    if args.watch is not None:
        if args.parameter_hash is not None:
            raise RuntimeError("--parameter-hash is supported for snapshots only.")
        if not 0 < args.watch <= 300 or not 0.001 <= args.interval <= 1:
            raise RuntimeError("Use 0 < --watch <= 300 and 0.001 <= --interval <= 1.")
        watch(pid, args.output, args.watch, args.interval, args.capture_active_curves)
        return
    if args.capture_active_curves:
        raise RuntimeError("--capture-active-curves requires --watch.")
    result = snapshot(pid, args.parameter_hash)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Saved {args.output}; PID={pid}, controller={result['controller']}, "
          f"parameters={len(result['parameters'])}, active={len(result['active_entries'])}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, AssertionError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
