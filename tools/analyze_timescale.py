import bisect
import json
import mmap
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'build' / 'analysis' / 'deps'))
import capstone


class PE:
    def __init__(self, path):
        self.path = Path(path)
        self.file = self.path.open('rb')
        self.data = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        pe = self.u32(0x3c)
        assert self.data[pe:pe+4] == b'PE\0\0'
        assert self.u16(pe+4) == 0x8664
        opt = pe+24
        assert self.u16(opt) == 0x20b
        self.base = self.u64(opt+24)
        self.sections = []
        table = opt+self.u16(pe+20)
        for i in range(self.u16(pe+6)):
            off = table+i*40
            name = self.data[off:off+8].rstrip(b'\0').decode('ascii')
            size, rva, raw_size, raw = struct.unpack_from('<IIII', self.data, off+8)
            self.sections.append(dict(name=name, rva=rva, size=size, raw=raw, raw_size=raw_size))
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        self.md.detail = True
        self.functions = []
        directory_rva, directory_size = struct.unpack_from('<II', self.data, opt+112+24)
        raw = self.raw(self.base+directory_rva)
        for off in range(raw, raw+directory_size, 12):
            begin, end, unwind = struct.unpack_from('<III', self.data, off)
            if begin:
                self.functions.append((self.base+begin, self.base+end, self.base+unwind))
        self.functions.sort()
        self.starts = [f[0] for f in self.functions]
        self.primary_cache = {}
        self.procedure_groups = None

    def u16(self, off): return struct.unpack_from('<H', self.data, off)[0]
    def u32(self, off): return struct.unpack_from('<I', self.data, off)[0]
    def u64(self, off): return struct.unpack_from('<Q', self.data, off)[0]

    def raw(self, va):
        rva = va-self.base
        for s in self.sections:
            if s['rva'] <= rva < s['rva']+s['raw_size']:
                return s['raw']+rva-s['rva']
        raise ValueError(f'VA not in file-backed section: {va:#x}')

    def va(self, raw):
        for s in self.sections:
            if s['raw'] <= raw < s['raw']+s['raw_size']:
                return self.base+s['rva']+raw-s['raw']
        raise ValueError(f'Raw offset not in section: {raw:#x}')

    def read(self, va, size):
        raw = self.raw(va)
        data = self.data[raw:raw+size]
        assert len(data) == size
        return data

    def q(self, va): return self.u64(self.raw(va))

    def string(self, va):
        if va == 0: return None
        raw = self.raw(va)
        end = self.data.find(b'\0', raw, raw+1024)
        if end == -1: raise ValueError(f'Unterminated string: {va:#x}')
        return self.data[raw:end].decode('ascii')

    def strings(self, value):
        pattern = re.compile(b'\0'+re.escape(value.encode('ascii'))+b'\0')
        return [self.va(m.start()+1) for m in pattern.finditer(self.data)]

    def pointers_to(self, va):
        return [self.va(m.start()) for m in re.finditer(re.escape(struct.pack('<Q',va)),self.data)]

    def type_name(self, va):
        kind = self.read(va+4, 1)[0]
        offset = {0:0x10, 1:0x18, 2:0x18, 3:0x10, 4:0x40, 5:0x10, 6:0x10, 7:0x10}[kind]
        return self.string(self.q(va+offset))

    def compound(self, va):
        raw = self.raw(va)
        assert self.data[raw+4] == 4
        name = self.string(self.u64(raw+0x40))
        num_bases = self.data[raw+6]
        num_attrs = self.u16(raw+0x0a)
        result = dict(name=name, va=hex(va), rva=hex(va-self.base), size=self.u32(raw+0x10),
                      constructor=hex(self.u64(raw+0x18)), bases=[], attrs=[])
        bases = self.u64(raw+0x58)
        for i in range(num_bases):
            item = self.raw(bases+i*0x10)
            result['bases'].append(dict(type=self.type_name(self.u64(item)),offset=self.u32(item+8)))
        attrs = self.u64(raw+0x60)
        for i in range(num_attrs):
            item = self.raw(attrs+i*0x38)
            name_ptr = self.u64(item+0x10)
            if name_ptr == 0:
                continue
            type_ptr = self.u64(item)
            if type_ptr == 0:
                continue
            result['attrs'].append(dict(name=self.string(name_ptr), type=self.type_name(type_ptr),
                offset=self.u16(item+8), flags=self.u16(item+10),
                getter=hex(self.u64(item+0x18)),setter=hex(self.u64(item+0x20)),record=hex(self.va(item))))
        return result

    def find_compounds(self, name):
        found = []
        for string in self.strings(name):
            for ptr in self.pointers_to(string):
                descriptor = ptr-0x40
                try:
                    record = self.compound(descriptor)
                    if record['name'] == name: found.append(record)
                except (ValueError, KeyError, UnicodeError, AssertionError):
                    pass
        return found

    def function(self, va):
        index = bisect.bisect_right(self.starts, va)-1
        if index >= 0:
            entry = self.functions[index]
            if entry[0] <= va < entry[1]: return entry
        return None

    def disasm(self, va, size):
        return self.md.disasm(self.read(va,size),va)

    def primary(self, entry):
        if entry in self.primary_cache: return self.primary_cache[entry]
        original = entry
        visited = set()
        while True:
            assert entry not in visited, 'Cyclic chained unwind information'
            visited.add(entry)
            hdr = self.read(entry[2],4)
            if not ((hdr[0] >> 3) & 4): break
            assert (hdr[0] & 7) in [1,2], 'Unsupported chained unwind version'
            address = entry[2]+4+((hdr[2]+1)&~1)*2
            values = struct.unpack('<III',self.read(address,12))
            entry = tuple(self.base+v for v in values)
        self.primary_cache[original] = entry
        return entry

    def procedure(self, va):
        entry = self.function(va)
        if entry is None: return None, []
        primary = self.primary(entry)
        if self.procedure_groups is None:
            self.procedure_groups = {}
            for f in self.functions:
                root = self.primary(f)
                self.procedure_groups.setdefault(root,[]).append(f)
        return primary,self.procedure_groups[primary]

    def procedure_insns(self, va):
        root, ranges = self.procedure(va)
        for begin,end,unwind in ranges:
            yield from self.disasm(begin,end-begin)

    def dump(self, va, limit=160):
        entry,ranges = self.procedure(va)
        print(f'PROCEDURE {entry[0]:#x} RVA {entry[0]-self.base:#x} RANGES {len(ranges)}')
        for count, ins in enumerate(self.procedure_insns(va)):
            if count >= limit:
                print('... truncated');break
            print(f'{ins.address:#x} {ins.bytes.hex(" "):28s} {ins.mnemonic:8s} {ins.op_str}')

    def rip_references(self, targets):
        text = next(s for s in self.sections if s['name'] == '.text')
        raw = text['raw']; size = min(text['size'],text['raw_size'])
        data = self.data[raw:raw+size]
        pattern = re.compile(rb'[\x40-\x4f][\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}',re.S)
        found = []
        for m in pattern.finditer(data):
            address = self.base+text['rva']+m.start()
            target = address+7+struct.unpack_from('<i',m.group(),3)[0]
            if target not in targets: continue
            ins = next(self.md.disasm(m.group(),address),None)
            if ins and ins.size == 7:
                found.append(dict(address=address,target=target,instruction=f'{ins.mnemonic} {ins.op_str}',function=self.function(address)))
        return found


def main():
    import argparse
    import hashlib
    parser = argparse.ArgumentParser(description="Offline evidence extraction for the verified DS2 1.10.89.0 executable.")
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("build/analysis/static-evidence.json"))
    args = parser.parse_args()
    digest = hashlib.sha256(args.game.read_bytes()).hexdigest().upper()
    expected = "BF3D1C665545930BC850D8F5DF486F7395885BB729D4FD408FDB03390DE0765B"
    if digest != expected:
        raise SystemExit(f"Unsupported executable SHA256: {digest}")
    pe = PE(args.game)
    names = ["DSTimeScaleControlParameter", "DSTimeScaleControlConfig", "SlowMotionSettingResource",
             "SlowMotionManagerGroup", "SlowMotionComponent", "SlowMotionEventInstance",
             "KJPSlowMotionEventResourceBase", "CurveResource", "CurveData", "CurvePoint", "Vec2Pack"]
    types = {name: pe.find_compounds(name) for name in names}
    for name, records in types.items():
        assert len(records) == 1, name
    parameter_fields = {a["name"]: a for a in types["DSTimeScaleControlParameter"][0]["attrs"]}
    assert parameter_fields["TimeScale"]["offset"] == 0x24
    assert parameter_fields["TimeScale"]["type"] == "float"
    assert parameter_fields["IsForEnemyDefeatedWithCloseCombat"]["offset"] == 0x65
    assert parameter_fields["IsForEnemyDefeatedWithFarCombat"]["offset"] == 0x66
    roles = {
        0x1089C20: "Contains immediate request Name 0x6ED5275D and calls the lookup function at RVA 0x1089D97",
        0x723740: "Registers SlowMotionManager::sExportedIsGameInSlowMotion with callback RVA 0x724530",
        0x7237E0: "Adds a request to the slow-motion manager array with stride 0x1c",
        0x723A70: "Changes the factors of an ID-selected slow-motion manager request",
        0x723BE0: "Removes or fades an ID-selected slow-motion manager request",
        0x724010: "Updates the slow-motion manager array and writes minimum factors at +0x20 and +0x24",
        0xD70E80: "Reads reflected time-control parameters and constructs a request",
        0xD70FE0: "Looks up a parameter by Name hash and calls the parameter-reading function",
        0xD712D0: "Adds an active request or resets timing for an existing matching Name value",
        0xD71E60: "Updates active requests and calculates three output factors",
        0xD717A0: "Changes active request expiration and removal-transition values",
        0xD71860: "Looks up an active request ID by Name value",
    }
    code = []
    for rva, role in roles.items():
        address = pe.base + rva
        primary, ranges = pe.procedure(address)
        instructions = list(pe.procedure_insns(address))
        assert instructions and instructions[0].address == address
        assert primary[0] == address
        record = {
            "rva": hex(rva), "preferred_va": hex(address), "analysis_role": role,
            "entry_bytes": pe.read(address, 16).hex(" "),
            "runtime_function_ranges": [[hex(b-pe.base), hex(e-pe.base)] for b,e,u in ranges],
            "disassembly": [{"rva": hex(i.address-pe.base), "bytes": i.bytes.hex(" "),
                "mnemonic": i.mnemonic, "operands": i.op_str} for i in instructions],
        }
        code.append(record)
    instruction = next(pe.disasm(pe.base+0xD70FF2,16))
    target = instruction.address+instruction.size+instruction.operands[1].mem.disp
    assert target-pe.base == 0x623E9A8
    slow_test = list(pe.disasm(pe.base + 0x724530, 0x2C))
    assert slow_test[-1].mnemonic == "ret"
    world_slot = slow_test[0].address + slow_test[0].size + slow_test[0].operands[1].mem.disp
    assert world_slot - pe.base == 0x623E338
    evidence = {
        "module": "DS2.exe", "sha256": digest, "preferred_image_base": hex(pe.base),
        "types": types, "code": code,
        "controller_pointer_slot": {"rva": hex(target-pe.base), "instruction_rva": "0xd70ff2",
            "instruction": instruction.mnemonic+" "+instruction.op_str},
        "slow_motion_test": {
            "rva": "0x724530", "registered_export": "SlowMotionManager::sExportedIsGameInSlowMotion",
            "world_pointer_slot_rva": hex(world_slot-pe.base), "manager_pointer_offset": "0x5d0",
            "tested_factor_offset": "0x20", "comparison_threshold": 1.0,
            "disassembly": [{"rva": hex(i.address-pe.base), "bytes": i.bytes.hex(" "),
                             "mnemonic": i.mnemonic, "operands": i.op_str} for i in slow_test],
        },
        "limitations": ["Analysis roles are descriptions, not recovered original function names.",
            "RUNTIME_FUNCTION entries are grouped using chained unwind information.",
            "Specific kill/knockout events are not identified by static analysis alone.",
            "Compound attribute count at +0x0a is verified for this executable, not generalized to other builds."],
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
    print(f"Saved {args.output}; {len(types)} reflected types, {len(code)} procedures.")


if __name__ == "__main__":
    main()
