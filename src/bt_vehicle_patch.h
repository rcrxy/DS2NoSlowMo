#pragma once

namespace BTVehiclePatch
{
    // DS2 1.10.89.0: the branch immediately before the vehicle's encounter
    // flag, shutdown flag and BlinkOff request are set. The global encounter
    // state, detector animation and time-control requests are not patched.
    constexpr std::uintptr_t BranchRVA = 0x1F8087D;

    bool WriteByte(std::uintptr_t address, unsigned char value)
    {
        SIZE_T written = 0;
        unsigned char actual = 0;
        return WriteProcessMemory(GetCurrentProcess(), reinterpret_cast<void *>(address),
                                  &value, sizeof(value), &written) && written == sizeof(value) &&
               TimeScalePatch::Read(address, actual) && actual == value;
    }

    void Run(const std::wstring &processPath, HANDLE log)
    {
        if (!TimeScalePatch::SupportedFile(processPath, log))
            return;
        const auto base = reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr));
        constexpr unsigned char entry[] = {0xC5, 0xFA, 0x11, 0x4C, 0x24, 0x10, 0x53, 0x48,
                                           0x83, 0xEC, 0x40, 0x80, 0x79, 0x3C, 0x00, 0x48};
        constexpr unsigned char window[] = {
            0x48, 0xB9, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF,
            0x48, 0x85, 0x88, 0xB0, 0x04, 0x00, 0x00, 0x75, 0x47,
            0x41, 0x80, 0x78, 0x1D, 0x00, 0x74, 0x40, 0xC6, 0x42, 0x3C, 0x01,
            0x83, 0xB8, 0x90, 0x04, 0x00, 0x00, 0x03, 0x75, 0x09,
            0xC6, 0x80, 0x4B, 0x0B, 0x00, 0x00, 0x01, 0xEB, 0x0A,
            0x81, 0x88, 0xF4, 0x04, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00};
        unsigned char actualEntry[sizeof(entry)]{}, actualWindow[sizeof(window)]{};
        if (!TimeScalePatch::Read(base + 0x1F806F0, actualEntry) ||
            std::memcmp(entry, actualEntry, sizeof(entry)) != 0 ||
            !TimeScalePatch::Read(base + 0x1F80865, actualWindow) ||
            std::memcmp(window, actualWindow, sizeof(window)) != 0)
        {
            TimeScalePatch::Log(log, "Disabled: BT vehicle runtime branch bytes differ.\r\n");
            return;
        }
        const auto address = base + BranchRVA;
        MEMORY_BASIC_INFORMATION region{};
        if (VirtualQuery(reinterpret_cast<const void *>(address), &region, sizeof(region)) != sizeof(region) ||
            region.State != MEM_COMMIT || region.Type != MEM_IMAGE ||
            region.AllocationBase != reinterpret_cast<void *>(base) ||
            region.Protect != PAGE_EXECUTE_READ)
        {
            TimeScalePatch::Log(log, "Disabled: BT vehicle code page validation failed.\r\n");
            return;
        }
        DWORD originalProtection = 0;
        if (!VirtualProtect(reinterpret_cast<void *>(address), 1, PAGE_EXECUTE_READWRITE, &originalProtection))
        {
            TimeScalePatch::Log(log, "Disabled: BT vehicle code page could not be made writable.\r\n");
            return;
        }
        // JZ +0x40 -> JMP +0x40. One byte; both instructions end at the same
        // address. The destination remains 0x1F808BF, the original return path.
        const bool applied = WriteByte(address, 0xEB) &&
                             FlushInstructionCache(GetCurrentProcess(), reinterpret_cast<const void *>(address), 1);
        if (!applied)
        {
            const bool restored = WriteByte(address, 0x74) &&
                                  FlushInstructionCache(GetCurrentProcess(), reinterpret_cast<const void *>(address), 1);
            TimeScalePatch::Log(log, "BT vehicle write failed: rollback=%d.\r\n", restored);
        }
        DWORD discarded = 0;
        const bool protectedAgain = VirtualProtect(reinterpret_cast<void *>(address), 1,
                                                    originalProtection, &discarded) != FALSE;
        if (!protectedAgain)
            TimeScalePatch::Log(log, "BT vehicle code page protection restore failed.\r\n");
        if (applied)
            TimeScalePatch::Log(log, "Applied: BT vehicle shutdown entry skipped at DS2.exe+0x1F8087D; protection_restored=%d.\r\n", protectedAgain);
    }
}
