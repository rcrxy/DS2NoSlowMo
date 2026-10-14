# DS2NoSlowMo

**Version:** 0.5.0-test · **Author:** zeco

**Game:** DEATH STRANDING 2: ON THE BEACH · Windows x64 / Steam

## Features

Three independent INI options:

| Option | Effect |
| --- | --- |
| Human defeat | Disable slowdown after killing or knocking out human enemies |
| Pickups | Disable pickup slowdown for cryptobiotes, electric bugs and chiral crystals |
| BT vehicles | Prevent forced vehicle shutdown and loss of control when entering a BT area |

Sounds and camera feedback can remain after the slowdown is removed. Vehicle behavior has been tested with a three-wheeled cruiser motorcycle and a truck; the Odradek sequence works normally.

## Compatibility

Supported tested Steam executable build: **1.10.89.0**. The plugin checks the exact executable and relevant runtime data or instructions. A build mismatch prevents the corresponding modification and is logged.

Other game builds, stores and mods editing the same data or instructions have not been verified. Human-detection slowdown, large-BT defeat effects and other triggers are outside the implemented scope of this release; their behavior under all option combinations has not been verified.

Vehicle sampling used the encounter-animation setting that plays only the first time. Other settings and other vehicle interruption events have not been tested.

## Installation

1. Exit the game completely.
2. Install **Ultimate ASI Loader, x64 version.dll**, beside `DS2.exe`. Download it from the [official project](https://github.com/ThirteenAG/Ultimate-ASI-Loader). Keep an existing working ASI loader setup.
3. Copy `DS2NoSlowMo.asi` and `DS2NoSlowMo.ini` beside `DS2.exe`.
4. Launch the game through Steam.

The loader is a separate dependency and is not bundled. The plugin creates `DS2NoSlowMo.log` beside the ASI.

## Configuration

Edit `DS2NoSlowMo.ini`:

```ini
[Features]
DisableHumanDefeatSlowMo=1
DisablePickupSlowMo=1
DisableBTVehicleShutdown=1
```

| Setting | Feature |
| --- | --- |
| `DisableHumanDefeatSlowMo` | Human-defeat slowdown |
| `DisablePickupSlowMo` | Pickup slowdown |
| `DisableBTVehicleShutdown` | BT-area vehicle shutdown |

`1` enables the modification; `0` keeps the original behavior. All default to `1` and work independently. An invalid value disables only that option and is logged.

**Restart the game after changing the INI.**

## Troubleshooting

Check `DS2NoSlowMo.log` for the plugin version and selected options:

- `Applied:`: modification applied.
- `Skipped:`: option set to `0`.
- `Disabled:`: validation or access failed.

If no log appears, check the loader and installation directory. When reporting a problem, provide the game version, plugin version, INI settings, reproduction steps and relevant log lines.

## Removal

To restore one effect, set its option to `0` and restart. To uninstall, exit the game and remove `DS2NoSlowMo.asi` and `DS2NoSlowMo.ini`. The generated log can also be removed. Keep an ASI loader used by other mods.

## License and credits

MIT License; see the included LICENSE. Author: zeco. Inspired by `plyrthn/ds2_sd_card_music_player`; original copyright notices are preserved. Ultimate ASI Loader is a separate project by ThirteenAG.
