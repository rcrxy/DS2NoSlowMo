#include <windows.h>

#include <cstdio>
#include <string>

#include "time_scale_patch.h"
#include "bt_vehicle_patch.h"

namespace
{
    constexpr char PluginVersion[] = "0.5.1";

    bool ReadSwitch(const std::wstring &iniPath, HANDLE log, const wchar_t *key, bool defaultEnabled, bool &enabled)
    {
        wchar_t value[64]{};
        const DWORD length = GetPrivateProfileStringW(L"Features", key, defaultEnabled ? L"1" : L"0",
                                                      value, ARRAYSIZE(value), iniPath.c_str());
        if (length != 1 || (value[0] != L'0' && value[0] != L'1'))
        {
            TimeScalePatch::Log(log, "Disabled: [Features] %ls must be 0 or 1.\r\n", key);
            return false;
        }
        enabled = value[0] == L'1';
        TimeScalePatch::Log(log, "Configuration: [Features] %ls=%d (default if omitted: %d).\r\n",
                            key, enabled, defaultEnabled);
        if (!enabled)
            TimeScalePatch::Log(log, "Skipped: %ls=0; effect unchanged.\r\n", key);
        return true;
    }

    std::wstring ModulePath(HMODULE module)
    {
        wchar_t buffer[32768];
        const DWORD length = GetModuleFileNameW(module, buffer, ARRAYSIZE(buffer));
        if (length == 0 || length >= ARRAYSIZE(buffer))
        {
            return {};
        }
        return {buffer, length};
    }

    std::string Utf8(const std::wstring &text)
    {
        const int length = static_cast<int>(text.size());
        const int bytes = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS,
                                              text.data(), length, nullptr, 0, nullptr, nullptr);
        if (bytes == 0)
        {
            return {};
        }
        std::string result(bytes, '\0');
        if (WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS,
                                text.data(), length, result.data(), bytes, nullptr, nullptr) != bytes)
        {
            return {};
        }
        return result;
    }

    DWORD WINAPI Initialize(LPVOID parameter)
    {
        const auto module = static_cast<HMODULE>(parameter);
        const std::wstring processPath = ModulePath(nullptr);
        const std::wstring pluginPath = ModulePath(module);
        const auto processSeparator = processPath.find_last_of(L'\\');
        const auto pluginSeparator = pluginPath.find_last_of(L'\\');
        if (processSeparator == std::wstring::npos ||
            pluginSeparator == std::wstring::npos)
        {
            OutputDebugStringA("DS2NoSlowMo: cannot read module paths.\n");
            return 1;
        }
        // The loader may also load ASIs into the game's helper processes.
        if (processPath.substr(processSeparator + 1) != L"DS2.exe")
        {
            return 0;
        }

        const std::wstring iniPath = pluginPath.substr(0, pluginSeparator + 1) + L"DS2NoSlowMo.ini";
        const std::wstring logPath = pluginPath.substr(0, pluginSeparator + 1) +
                                     L"DS2NoSlowMo.log";
        HANDLE log = CreateFileW(logPath.c_str(), GENERIC_WRITE,
                                 FILE_SHARE_READ, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (log == INVALID_HANDLE_VALUE)
        {
            OutputDebugStringA("DS2NoSlowMo: cannot create DS2NoSlowMo.log beside the ASI.\n");
            return 1;
        }

        SYSTEMTIME now{};
        GetLocalTime(&now);
        char header[256];
        const int headerLength = std::snprintf(header, sizeof(header),
                                               "DS2NoSlowMo loaded\r\nPlugin version: %s\r\nPID: %lu\r\n"
                                               "Local time: %04u-%02u-%02u %02u:%02u:%02u\r\n",
                                               PluginVersion, GetCurrentProcessId(), now.wYear, now.wMonth, now.wDay,
                                               now.wHour, now.wMinute, now.wSecond);
        if (headerLength <= 0 || static_cast<size_t>(headerLength) >= sizeof(header))
        {
            CloseHandle(log);
            return 1;
        }
        const std::string message = std::string(header, headerLength) +
                                    "Process: " + Utf8(processPath) + "\r\nPlugin: " + Utf8(pluginPath) +
                                    "\r\nConfiguration file: " + Utf8(iniPath) +
                                    "\r\nMode: configured slowdown curves and BT vehicle shutdown patch.\r\n";
        DWORD written = 0;
        const DWORD size = static_cast<DWORD>(message.size());
        const bool success = WriteFile(log, message.data(), size, &written, nullptr) &&
                             written == size;
        OutputDebugStringA(success ? "DS2NoSlowMo loaded.\n" : "DS2NoSlowMo: log write failed.\n");
        if (success)
        {
            try
            {
                bool enemyDefeat = false, pickup = false, btVehicle = false;
                const bool enemyValid = ReadSwitch(iniPath, log, L"DisableEnemyDefeatSlowMo", true, enemyDefeat);
                const bool pickupValid = ReadSwitch(iniPath, log, L"DisablePickupSlowMo", true, pickup);
                const bool btVehicleValid = ReadSwitch(iniPath, log, L"DisableBTVehicleShutdown", false, btVehicle);
                if (btVehicleValid && btVehicle)
                    BTVehiclePatch::Run(processPath, log);
                if ((enemyValid && enemyDefeat) || (pickupValid && pickup))
                    TimeScalePatch::Run(processPath, log, enemyValid && enemyDefeat, pickupValid && pickup);
                else if (!(btVehicleValid && btVehicle))
                    TimeScalePatch::Log(log, "No enabled effects; game data unchanged.\r\n");
            }
            catch (...)
            {
                TimeScalePatch::Log(log, "Disabled: initialization raised an exception.\r\n");
            }
        }
        CloseHandle(log);
        return success ? 0 : 1;
    }

} // namespace

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        // Disk I/O runs after DllMain returns; never wait for the worker here.
        // Keep thread notifications: /MT links the static CRT, which needs them.
        HANDLE thread = CreateThread(nullptr, 0, Initialize, module, 0, nullptr);
        if (thread == nullptr)
        {
            OutputDebugStringA("DS2NoSlowMo: initialization thread creation failed.\n");
            return FALSE;
        }
        CloseHandle(thread);
    }
    return TRUE;
}
