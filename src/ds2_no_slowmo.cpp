#include <windows.h>

#include <cstdio>
#include <string>

#include "time_scale_patch.h"
#include "bt_vehicle_patch.h"

namespace
{
    constexpr char PluginVersion[] = "0.6.2";

    bool TryReadSwitch(const std::wstring &iniPath, const wchar_t *section, const wchar_t *key,
                       bool defaultEnabled, bool &enabled)
    {
        wchar_t value[64]{};
        const DWORD length = GetPrivateProfileStringW(section, key, defaultEnabled ? L"1" : L"0",
                                                      value, ARRAYSIZE(value), iniPath.c_str());
        if (length != 1 || (value[0] != L'0' && value[0] != L'1'))
            return false;
        enabled = value[0] == L'1';
        return true;
    }

    bool ReadSwitch(const std::wstring &iniPath, HANDLE &log, const wchar_t *key, bool defaultEnabled, bool &enabled)
    {
        if (!TryReadSwitch(iniPath, L"Features", key, defaultEnabled, enabled))
        {
            TimeScalePatch::Log(log, "Disabled: [Features] %ls must be 0 or 1.\r\n", key);
            return false;
        }
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

    void StartLog(HANDLE &log, const std::wstring &logPath, const std::wstring &processPath,
                  const std::wstring &pluginPath, const std::wstring &iniPath)
    {
        log = CreateFileW(logPath.c_str(), GENERIC_WRITE,
                          FILE_SHARE_READ, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (log == INVALID_HANDLE_VALUE)
            OutputDebugStringA("DS2NoSlowMo: cannot create DS2NoSlowMo.log; using debug output.\n");

        SYSTEMTIME now{};
        GetLocalTime(&now);
        TimeScalePatch::Log(log, "DS2NoSlowMo loaded\r\nPlugin version: %s\r\nPID: %lu\r\n"
                                 "Local time: %04u-%02u-%02u %02u:%02u:%02u\r\n",
                            PluginVersion, GetCurrentProcessId(), now.wYear, now.wMonth, now.wDay,
                            now.wHour, now.wMinute, now.wSecond);
        const std::string message = "Process: " + Utf8(processPath) + "\r\nPlugin: " + Utf8(pluginPath) +
                                    "\r\nConfiguration file: " + Utf8(iniPath) +
                                    "\r\nMode: configured slowdown curves and BT vehicle shutdown patch.\r\n";
        TimeScalePatch::WriteLog(log, message.c_str(), static_cast<DWORD>(message.size()));
        if (log != INVALID_HANDLE_VALUE)
            OutputDebugStringA("DS2NoSlowMo loaded.\n");
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
            return 1;
        // The loader may also load ASIs into the game's helper processes.
        if (processPath.substr(processSeparator + 1) != L"DS2.exe")
        {
            return 0;
        }

        const std::wstring iniPath = pluginPath.substr(0, pluginSeparator + 1) + L"DS2NoSlowMo.ini";
        HANDLE log = nullptr;
        bool loggingEnabled = false;
        if (TryReadSwitch(iniPath, L"Logging", L"EnableLogging", false, loggingEnabled) && loggingEnabled)
        {
            log = INVALID_HANDLE_VALUE;
            try
            {
                const std::wstring logPath = pluginPath.substr(0, pluginSeparator + 1) + L"DS2NoSlowMo.log";
                StartLog(log, logPath, processPath, pluginPath, iniPath);
            }
            catch (...)
            {
                OutputDebugStringA("DS2NoSlowMo: cannot complete startup logging.\n");
            }
        }

        try
        {
            bool enemyDefeat = false, pickup = false, btVehicle = false, detection = false;
            const bool enemyValid = ReadSwitch(iniPath, log, L"DisableEnemyDefeatSlowMo", true, enemyDefeat);
            const bool pickupValid = ReadSwitch(iniPath, log, L"DisablePickupSlowMo", true, pickup);
            const bool btVehicleValid = ReadSwitch(iniPath, log, L"DisableBTVehicleShutdown", false, btVehicle);
            const bool detectionValid = ReadSwitch(iniPath, log, L"DisableDetectionSlowMo", false, detection);
            if (btVehicleValid && btVehicle)
                BTVehiclePatch::Run(processPath, log);
            if ((enemyValid && enemyDefeat) || (pickupValid && pickup) || (detectionValid && detection))
                TimeScalePatch::Run(processPath, log, enemyValid && enemyDefeat, pickupValid && pickup,
                                    detectionValid && detection);
            else if (!(btVehicleValid && btVehicle))
                TimeScalePatch::Log(log, "No enabled effects; game data unchanged.\r\n");
        }
        catch (...)
        {
            TimeScalePatch::Log(log, "Disabled: initialization raised an exception.\r\n");
        }
        if (log != nullptr && log != INVALID_HANDLE_VALUE)
            CloseHandle(log);
        return 0;
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
            return FALSE;
        CloseHandle(thread);
    }
    return TRUE;
}
