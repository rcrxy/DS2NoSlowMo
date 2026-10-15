# DS2NoSlowMo

**Version:** 0.5.1 · **Author:** zeco

**Game:** DEATH STRANDING 2: ON THE BEACH · Windows x64 / Steam

## Features

Three independent INI options:

| Option | Effect |
| --- | --- |
| Enemy defeat | Disable slowdown after defeating enemies; tested with human and machine enemies |
| Pickups | Disable pickup slowdown for cryptobiotes, electric bugs and chiral crystals |
| BT vehicles | Prevent forced vehicle shutdown and loss of control when entering a BT area (disabled by default) |

Sounds and camera feedback can remain after the slowdown is removed. Vehicle behavior has been tested with a three-wheeled cruiser motorcycle and a truck; the Odradek sequence works normally.

## Compatibility

Minimum executable file version: **1.10.89.0**. Tested Steam build: **1.10.89.0**. The plugin compares all four numeric file-version components and accepts this version or newer. Older versions or unreadable version information prevent modifications and are logged. The executable no longer needs to match an exact SHA256.

Runtime instruction, data-layout and curve checks remain in place; a mismatch prevents the corresponding modification. Passing the minimum-version check does not confirm compatibility with a newer build.

Other game builds, stores and mods editing the same data or instructions have not been verified. Human-detection slowdown, large-BT defeat effects and other triggers are outside the implemented scope of this release; their behavior under all option combinations has not been verified.

Vehicle sampling used the encounter-animation setting that plays only the first time. Other settings and other vehicle interruption events have not been tested.

## Installation

1. Exit the game completely.
2. Copy the included `DS2NoSlowMo.asi` and `DS2NoSlowMo.ini` beside `DS2.exe`.
3. If you do not have an ASI loader, copy the included `version.dll` into the same directory. Otherwise, keep your working loader's DLL and configuration.
4. Launch the game through Steam.

Ultimate ASI Loader **9.7.4 x64** is included; no separate download is required. The plugin creates `DS2NoSlowMo.log` beside the ASI.

## Configuration

Edit `DS2NoSlowMo.ini`:

```ini
[Features]
DisableEnemyDefeatSlowMo=1
DisablePickupSlowMo=1
DisableBTVehicleShutdown=0
```

| Setting | Feature |
| --- | --- |
| `DisableEnemyDefeatSlowMo` | Enemy-defeat slowdown (human and machine enemies) |
| `DisablePickupSlowMo` | Pickup slowdown |
| `DisableBTVehicleShutdown` | BT-area vehicle shutdown |

`1` enables the modification; `0` keeps the original behavior. Enemy-defeat and pickup options default to `1`; `DisableBTVehicleShutdown` defaults to `0`, preserving the original game mechanic. These defaults also apply when an option is omitted. All options work independently. An invalid value disables only that option and is logged.

`DisableHumanDefeatSlowMo` has been renamed to `DisableEnemyDefeatSlowMo`. Update the key in existing INI files.

**Restart the game after changing the INI.**

## Troubleshooting

Check `DS2NoSlowMo.log` for the plugin version and selected options:

- `Applied:`: modification applied.
- `Skipped:`: option set to `0`.
- `Disabled:`: validation or access failed.

If no log appears, check the loader and installation directory. When reporting a problem, provide the game version, plugin version, INI settings, reproduction steps and relevant log lines.

## Removal

To restore one effect, set its option to `0` and restart. To uninstall, exit the game and remove `DS2NoSlowMo.asi` and `DS2NoSlowMo.ini`. The generated log can also be removed. Remove the bundled `version.dll` only if you installed it for this mod and no other mods need it.

## License and credits

MIT License; see the included LICENSE. Author: zeco. Inspired by `plyrthn/ds2_sd_card_music_player`; original copyright notices are preserved. The bundled [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) is by ThirteenAG and uses the MIT License; see `LICENSE-Ultimate-ASI-Loader.txt`.
