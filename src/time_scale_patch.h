#pragma once

#include <bcrypt.h>
#include <array>
#include <cstdarg>
#include <cstdint>
#include <cstring>
#include <vector>

#pragma comment(lib, "bcrypt.lib")

namespace TimeScalePatch
{
    enum class Effect { HumanDefeat, Pickup };
    constexpr std::uint32_t HumanDefeatName = 0x4152CF0A;
    constexpr std::uint32_t PickupName = 0x6ED5275D;

    std::uint32_t Name(Effect effect)
    {
        return effect == Effect::Pickup ? PickupName : HumanDefeatName;
    }
    constexpr std::uintptr_t ControllerSlot = 0x623E9A8;
    constexpr std::uintptr_t ParameterRTTI = 0xD708E0;
    constexpr std::uintptr_t CurveRTTI = 0x1B30D90;

    void Log(HANDLE file, const char *format, ...)
    {
        char buffer[512];
        va_list args;
        va_start(args, format);
        const int length = std::vsnprintf(buffer, sizeof(buffer), format, args);
        va_end(args);
        if (length > 0 && static_cast<size_t>(length) < sizeof(buffer))
        {
            DWORD written = 0;
            WriteFile(file, buffer, static_cast<DWORD>(length), &written, nullptr);
            FlushFileBuffers(file);
        }
    }

    bool Read(std::uintptr_t address, void *data, size_t size)
    {
        SIZE_T read = 0;
        return ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<const void *>(address),
                                 data, size, &read) && read == size;
    }

    template <typename T> bool Read(std::uintptr_t address, T &value)
    {
        return Read(address, &value, sizeof(value));
    }

    bool SupportedFile(const std::wstring &path)
    {
        constexpr unsigned char expected[] = {
            0xBF, 0x3D, 0x1C, 0x66, 0x55, 0x45, 0x93, 0x0B, 0xC8, 0x50, 0xD8, 0xF5, 0xDF, 0x48, 0x6F, 0x73,
            0x95, 0x88, 0x5B, 0xB7, 0x29, 0xD4, 0xFD, 0x40, 0x8F, 0xDB, 0x03, 0x39, 0x0D, 0xE0, 0x76, 0x5B};
        std::array<unsigned char, 32> digest{};
        BCRYPT_ALG_HANDLE algorithm = nullptr;
        BCRYPT_HASH_HANDLE hash = nullptr;
        HANDLE file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
                                  FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN, nullptr);
        if (file == INVALID_HANDLE_VALUE)
            return false;
        bool success = false;
        if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) >= 0)
        {
            DWORD size = 0, copied = 0;
            if (BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, reinterpret_cast<PUCHAR>(&size),
                                  sizeof(size), &copied, 0) >= 0)
            {
                std::vector<unsigned char> object(size);
                if (BCryptCreateHash(algorithm, &hash, object.data(), size, nullptr, 0, 0) >= 0)
                {
                    unsigned char buffer[65536];
                    DWORD bytes = 0;
                    success = true;
                    for (;;)
                    {
                        if (!ReadFile(file, buffer, sizeof(buffer), &bytes, nullptr))
                        {
                            success = false;
                            break;
                        }
                        if (bytes == 0)
                            break;
                        if (BCryptHashData(hash, buffer, bytes, 0) < 0)
                        {
                            success = false;
                            break;
                        }
                    }
                    success = success && BCryptFinishHash(hash, digest.data(), static_cast<ULONG>(digest.size()), 0) >= 0;
                    BCryptDestroyHash(hash);
                    hash = nullptr;
                }
            }
            BCryptCloseAlgorithmProvider(algorithm, 0);
        }
        CloseHandle(file);
        return success && std::memcmp(digest.data(), expected, sizeof(expected)) == 0;
    }

    struct ArrayHeader
    {
        std::int32_t count;
        std::int32_t capacity;
        std::uintptr_t data;
    };
    static_assert(sizeof(ArrayHeader) == 0x10);

    struct CurvePoint
    {
        float x, y, inTangent, outTangent, inTangentX, outTangentX;
    };
    static_assert(sizeof(CurvePoint) == 0x18);

    struct CurveEdit
    {
        std::uintptr_t address;
        ArrayHeader array;
        std::vector<CurvePoint> points;
        float originalLowest;
    };

    bool PrepareCurve(std::uintptr_t base, std::uintptr_t address,
                      const std::vector<std::array<float, 2>> &expected, CurveEdit &edit)
    {
        std::uintptr_t vtable = 0, getter = 0;
        if (!Read(address, vtable) || !Read(vtable, getter) || getter != base + CurveRTTI)
            return false;
        ArrayHeader header{};
        if (!Read(address + 0x20, header) || header.count != static_cast<std::int32_t>(expected.size()) ||
            header.capacity < header.count || header.capacity > 4096 || header.data == 0)
            return false;
        edit = {address, header, std::vector<CurvePoint>(expected.size()), 0.0f};
        if (!Read(header.data, edit.points.data(), edit.points.size() * sizeof(CurvePoint)) ||
            !Read(address + 0x38, edit.originalLowest))
            return false;
        for (size_t i = 0; i < expected.size(); ++i)
        {
            const auto &point = edit.points[i];
            if (point.x != expected[i][0] || point.y != expected[i][1] ||
                point.inTangent != 0.0f || point.outTangent != 0.0f ||
                point.inTangentX != 1.0f || point.outTangentX != 1.0f)
                return false;
        }
        return true;
    }

    bool WriteFloat(std::uintptr_t address, float value)
    {
        MEMORY_BASIC_INFORMATION region{};
        if (VirtualQuery(reinterpret_cast<const void *>(address), &region, sizeof(region)) != sizeof(region) ||
            region.State != MEM_COMMIT || (region.Protect & (PAGE_GUARD | PAGE_NOACCESS)) ||
            (region.Protect & 0xFF) != PAGE_READWRITE ||
            address + sizeof(value) > reinterpret_cast<std::uintptr_t>(region.BaseAddress) + region.RegionSize)
            return false;
        SIZE_T written = 0;
        float actual = 0.0f;
        return WriteProcessMemory(GetCurrentProcess(), reinterpret_cast<void *>(address), &value,
                                  sizeof(value), &written) && written == sizeof(value) &&
               Read(address, actual) && actual == value;
    }

    bool ApplyCurve(const CurveEdit &edit, bool restore)
    {
        bool success = true;
        for (size_t i = 0; i < edit.points.size(); ++i)
            success = WriteFloat(edit.array.data + i * sizeof(CurvePoint) + 4,
                                 restore ? edit.points[i].y : 1.0f) && success;
        return WriteFloat(edit.address + 0x38, restore ? edit.originalLowest : 1.0f) && success;
    }

    // 0: retry until resources exist / requests finish; 1: applied; -1: reject this layout.
    int TryApply(std::uintptr_t base, HANDLE log, Effect effect)
    {
        const bool pickup = effect == Effect::Pickup;
        const auto targetName = Name(effect);
        std::uintptr_t controller = 0;
        if (!Read(base + ControllerSlot, controller) || !controller)
            return 0;
        ArrayHeader table{}, active{};
        if (!Read(controller + 0x18, table) || !Read(controller + 0x28, active))
            return -1;
        if (table.count == 0 || active.count != 0)
            return 0;
        if (table.count < 0 || table.count > 4096 || table.capacity < table.count || table.data == 0)
            return -1;
        std::vector<std::uintptr_t> parameters(static_cast<size_t>(table.count));
        if (!Read(table.data, parameters.data(), parameters.size() * sizeof(std::uintptr_t)))
            return -1;
        std::uintptr_t target = 0;
        std::array<std::uintptr_t, 3> curves{};
        for (auto pointer : parameters)
        {
            std::uint32_t name = 0;
            if (!Read(pointer + 0x20, name))
                return -1;
            if (name == targetName)
            {
                if (target)
                    return -1;
                target = pointer;
                if (!Read(pointer + 0x40, curves))
                    return -1;
            }
        }
        if (!target)
            return 0;
        std::uintptr_t vtable = 0, getter = 0;
        std::array<float, 6> settings{};
        std::uint32_t priority = 0;
        unsigned char shortSlow = 0;
        if (!Read(target, vtable) || !Read(vtable, getter) || getter != base + ParameterRTTI ||
            !Read(target + 0x24, settings) || !Read(target + 0x60, priority) ||
            !Read(target + 0x68, shortSlow) || priority != (pickup ? 16u : 17u) ||
            shortSlow != (pickup ? 1 : 0) ||
            settings != std::array<float, 6>{1.0f, 1.0f, 1.0f, pickup ? 1.0f : 1.75f, 0.1f, 0.1f} ||
            !curves[0] || !curves[1] ||
            (pickup ? (curves[0] != curves[1] || curves[0] != curves[2])
                    : (curves[0] == curves[1] || curves[2] != 0)))
            return -1;
        for (auto pointer : parameters)
        {
            if (pointer == target)
                continue;
            std::array<std::uintptr_t, 3> other{};
            if (!Read(pointer + 0x40, other))
                return -1;
            for (auto curve : other)
                if (curve && (curve == curves[0] || curve == curves[1] || curve == curves[2]))
                    return -1;
        }
        std::vector<CurveEdit> edits(pickup ? 1 : 2);
        if (pickup)
        {
            // All three channels point to the same verified CurveResource; edit it once.
            if (!PrepareCurve(base, curves[0], {{0, 0.051f}, {0.45f, 0.051f}, {0.55f, 1}, {1, 1}}, edits[0]))
                return -1;
        }
        else if (!PrepareCurve(base, curves[0], {{0, 1}, {0.11f, 1}, {0.2f, 0.051f}, {0.7f, 0.051f},
                                               {1.1f, 0.3f}, {1.785f, 0.051f}, {1.8f, 0.051f}}, edits[0]) ||
                 !PrepareCurve(base, curves[1], {{0, 1}, {0.11f, 1}, {0.2f, 0.25f}, {0.75f, 0.25f},
                                               {0.8f, 0.1f}, {1.2f, 0.1f}, {1.7f, 0.5f}, {1.8f, 0.5f}}, edits[1]))
            return -1;
        ArrayHeader after{};
        std::uintptr_t current = 0;
        if (!Read(base + ControllerSlot, current) || current != controller ||
            !Read(controller + 0x18, after) || std::memcmp(&table, &after, sizeof(table)) != 0 ||
            !Read(controller + 0x28, after) || after.count != 0)
            return 0;
        bool applied = true;
        for (const auto &edit : edits)
        {
            if (!ApplyCurve(edit, false))
            {
                applied = false;
                break;
            }
        }
        if (!applied)
        {
            bool restored = true;
            for (const auto &edit : edits)
                restored = ApplyCurve(edit, true) && restored;
            Log(log, "Patch write failed: Name=0x%08X; rollback=%d.\r\n", targetName, restored);
            return -1;
        }
        Log(log, "Applied: Name=0x%08X; %zu curve(s); all Y=1.0.\r\n", targetName, edits.size());
        return 1;
    }

    void Run(const std::wstring &processPath, HANDLE log, bool humanDefeat, bool pickup)
    {
        if (!SupportedFile(processPath))
        {
            Log(log, "Disabled: executable SHA256 is unsupported or could not be read.\r\n");
            return;
        }
        const auto base = reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr));
        const unsigned char expected[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x7C,
                                          0x24, 0x10, 0x55, 0x48, 0x8D, 0x6C, 0x24, 0xB1};
        unsigned char actual[sizeof(expected)]{};
        if (!Read(base + 0xD70E80, actual) || std::memcmp(actual, expected, sizeof(expected)) != 0)
        {
            Log(log, "Disabled: runtime entry bytes differ at DS2.exe+0xD70E80.\r\n");
            return;
        }
        Log(log, "Waiting for enabled parameters and an idle request array (up to 10 minutes).\r\n");
        const std::array<Effect, 2> effects{Effect::HumanDefeat, Effect::Pickup};
        std::array<bool, 2> pending{humanDefeat, pickup};
        for (unsigned int attempt = 0; attempt < 1200; ++attempt)
        {
            for (size_t i = 0; i < effects.size(); ++i)
            {
                if (!pending[i])
                    continue;
                const int result = TryApply(base, log, effects[i]);
                if (result == 0)
                    continue;
                pending[i] = false;
                if (result < 0)
                    Log(log, "Disabled: Name=0x%08X parameter/curve validation or memory access failed.\r\n", Name(effects[i]));
            }
            if (!pending[0] && !pending[1])
                return;
            Sleep(500);
        }
        for (size_t i = 0; i < effects.size(); ++i)
            if (pending[i])
                Log(log, "Disabled: Name=0x%08X did not become available within 10 minutes.\r\n", Name(effects[i]));
    }
}
