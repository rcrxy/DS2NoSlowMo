# N 网页面说明

## Title

DS2NoSlowMo - Slow Motion and BT Vehicle Shutdown Toggles

## Summary

Independent INI options to disable human-defeat and pickup slowdowns, and prevent forced vehicle shutdowns when entering BT areas. Supports the tested Steam executable build 1.10.89.0.

## Description

### Features

DS2NoSlowMo provides three independent options for DEATH STRANDING 2: ON THE BEACH:

- Disable slowdown after killing or knocking out human enemies.
- Disable pickup slowdown for cryptobiotes, electric bugs and chiral crystals.
- Prevent forced vehicle shutdown and loss of control when entering BT areas.

Sounds and camera feedback can remain after the slowdown is removed. The vehicle feature has been tested with a three-wheeled cruiser motorcycle and a truck; the Odradek sequence works normally.

### Requirements

Windows x64 / Steam, tested executable build **1.10.89.0**, and **Ultimate ASI Loader (x64 version.dll)** from its [official project](https://github.com/ThirteenAG/Ultimate-ASI-Loader).

The loader is not bundled. An existing working ASI loader setup can be kept.

### Installation

1. Exit the game.
2. Install the loader beside `DS2.exe`.
3. Copy `DS2NoSlowMo.asi` and `DS2NoSlowMo.ini` into that directory.
4. Launch through Steam.

### Configuration

```ini
[Features]
DisableHumanDefeatSlowMo=1
DisablePickupSlowMo=1
DisableBTVehicleShutdown=1
```

The settings control human-defeat slowdown, pickup slowdown and BT-area vehicle shutdown, respectively.

`1` enables the modification; `0` keeps the original effect. All default to `1` and work independently. **Restart after changing the INI.**

### Compatibility and scope

The plugin checks the exact game executable and relevant runtime data or instructions. A build mismatch prevents the corresponding modification and is logged. Other versions, stores and mods editing the same data or instructions have not been verified.

Human-detection slowdown, large-BT defeat effects and other triggers are outside this release's implemented scope; their behavior under all option combinations has not been verified. Vehicle sampling used the encounter-animation setting that plays only the first time. Other settings and vehicle interruption events have not been tested.

### Troubleshooting and removal

Check `DS2NoSlowMo.log`: `Applied:` means success, `Skipped:` means an option is disabled, and `Disabled:` means validation or access failed. If no log appears, check the loader and installation directory.

To uninstall, exit the game and remove the ASI and INI. Keep the loader if other mods require it.

For support, include game and plugin versions, enabled options, reproduction steps and relevant log lines.

### Credits

Author: **zeco**. MIT License, including original copyright notices. Inspired by `plyrthn/ds2_sd_card_music_player`. Ultimate ASI Loader is a separate project by ThirteenAG.

## File description

0.5.0-test — Independent options for human-defeat slowdown, pickup slowdown and BT-area vehicle shutdown. Includes the ASI, INI, installation guide and MIT license. ASI Loader required separately.
