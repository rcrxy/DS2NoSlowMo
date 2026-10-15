# N 网页面说明

## Title

DS2NoSlowMo - Slow Motion and BT Vehicle Shutdown Toggles

## Summary

Independent INI options to disable enemy-defeat and pickup slowdowns, and optionally prevent forced vehicle shutdowns when entering BT areas. Requires executable file version 1.10.89.0 or newer; tested on Steam build 1.10.89.0.

## Description

### Features

DS2NoSlowMo provides three independent options for DEATH STRANDING 2: ON THE BEACH:

- Disable slowdown after defeating enemies; tested with human and machine enemies.
- Disable pickup slowdown for cryptobiotes, electric bugs and chiral crystals.
- Prevent forced vehicle shutdown and loss of control when entering BT areas (disabled by default).

Sounds and camera feedback can remain after the slowdown is removed. The vehicle feature has been tested with a three-wheeled cruiser motorcycle and a truck; the Odradek sequence works normally.

### Requirements

Windows x64 / Steam, executable file version **1.10.89.0 or newer**. Tested build: **1.10.89.0**.

**Ultimate ASI Loader 9.7.4 (x64 version.dll) is included. No separate download is required.** An existing working ASI loader setup can be kept.

### Installation

1. Exit the game.
2. Copy the included `DS2NoSlowMo.asi` and `DS2NoSlowMo.ini` beside `DS2.exe`.
3. If you do not have an ASI loader, copy the included `version.dll` into the same directory. Otherwise, keep your working loader's DLL and configuration.
4. Launch through Steam.

### Configuration

```ini
[Features]
DisableEnemyDefeatSlowMo=1
DisablePickupSlowMo=1
DisableBTVehicleShutdown=0
```

The settings control enemy-defeat slowdown, pickup slowdown and BT-area vehicle shutdown, respectively.

`1` enables the modification; `0` keeps the original effect. Enemy-defeat and pickup options default to `1`; `DisableBTVehicleShutdown` defaults to `0`, preserving the original game mechanic. These defaults also apply when an option is omitted. All options work independently. **Restart after changing the INI.**

`DisableHumanDefeatSlowMo` has been renamed to `DisableEnemyDefeatSlowMo`. Update the key in existing INI files.

### Compatibility and scope

The plugin compares all four numeric executable file-version components against the minimum **1.10.89.0**. Older versions or unreadable version information prevent modifications and are logged; an exact executable SHA256 is no longer required. Runtime instruction, data-layout and curve checks remain in place, and a mismatch prevents the corresponding modification. Newer builds still require those checks to pass and have not been verified in-game. Other stores and mods editing the same data or instructions have not been verified.

Human-detection slowdown, large-BT defeat effects and other triggers are outside this release's implemented scope; their behavior under all option combinations has not been verified. Vehicle sampling used the encounter-animation setting that plays only the first time. Other settings and vehicle interruption events have not been tested.

### Troubleshooting and removal

Check `DS2NoSlowMo.log`: `Applied:` means success, `Skipped:` means an option is disabled, and `Disabled:` means validation or access failed. If no log appears, check the loader and installation directory.

To uninstall, exit the game and remove the ASI and INI. Remove the bundled `version.dll` only if you installed it for this mod and no other mods need it.

For support, include game and plugin versions, enabled options, reproduction steps and relevant log lines.

### Credits

Author: **zeco**. MIT License, including original copyright notices. Inspired by `plyrthn/ds2_sd_card_music_player`. The bundled [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) is by ThirteenAG, under the MIT License; its license is included as `LICENSE-Ultimate-ASI-Loader.txt`.

## File description

0.5.1 — Independent options for enemy-defeat slowdown, pickup slowdown and BT-area vehicle shutdown (disabled by default). Includes the ASI, INI, Ultimate ASI Loader 9.7.4 x64, installation guide and both MIT license files. No separate loader download required.
