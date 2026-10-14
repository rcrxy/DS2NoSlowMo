# DS2NoSlowMo

《死亡搁浅 2》慢动作修改项目。提供人类敌人击败与拾取慢动作的独立配置开关。

`0.2.0-test` 针对单次击倒实测对应的 `Name=0x4152CF0A`，将其世界及玩家倍率曲线改为恒定 `1.0`。修改后两次游戏内击昏测试均记录到该请求，已监测的倍率始终为 `1.0`；用户反馈操作延迟似乎消失，音效和镜头特效仍在。它保留原有请求和计时流程；不同击倒方式、重载资源及其他触发场景尚未验证。

用户后续清理区域及无 Mod 对照反馈：当前版明显改善击杀后 Sam 的移动受阻；原版有约 1～2 秒的时停体感，期间再次击杀会重置效果。这部分未同步采样，极短残留体感的来源仍未确认。遇敌时停暂不处理。

当前版本 `0.4.0-test`。三轮单独采样确认隐生虫、电气虫、开罗尔晶体均使用 `Name=0x6ED5275D`，共用一条倍率曲线。拾取开关将该曲线设为恒定 `1.0`；修改后隐生虫多次拾取实测没有慢动作，采样倍率全程为 `1.0`，用户随后确认电气虫、晶体也生效。这两项修改后测试没有同步采样；其他场景是否使用此请求尚未排除。

## 配置

将 [DS2NoSlowMo.ini](DS2NoSlowMo.ini) 放在 `DS2NoSlowMo.asi` 同一目录：

```ini
[Features]
DisableHumanDefeatSlowMo=1
DisablePickupSlowMo=1
```

- `DisableHumanDefeatSlowMo`：控制已验证的人类敌人击败请求。
- `DisablePickupSlowMo`：控制三种拾取实测的共享请求。
- 每项 `1` 为禁用该请求的倍率减速，`0` 为保留原效果；缺省均为 `1`。其他值会停止应用该项并记入日志，另一项独立读取。

配置只在插件启动时读取，修改后需完整退出并重启游戏。两个开关不绑定。

## 开发

```powershell
.\do_build.bat Debug
.\do_build.bat Release
```

默认构建 Release。产物分别位于 `build/Debug/` 和 `build/Release/`。
构建脚本自动查找已安装的 Visual Studio C++ 工具链。本机使用 VS2026；无需额外 Hook 库，SHA256 校验使用 Windows 系统的 BCrypt。

## 加载验证

退出游戏，将构建出的 `DS2NoSlowMo.asi`、`DS2NoSlowMo.ini` 与 x64 ASI Loader 的 `version.dll` 放到 `DS2.exe` 同一目录，再通过 Steam 启动游戏。

日志还会记录 PID、插件版本、进程路径和插件路径。核对这些信息后，才能确认加载到了实际游戏进程。

测试版只有在游戏 SHA256、运行时代码、参数类型、曲线点数据及参数表内引用检查全部通过，且时间控制请求数组为空时才修改曲线。成功日志分别包含 `Applied: Name=0x4152CF0A` 和 `Applied: Name=0x6ED5275D`；`Skipped:` 表示配置关闭该项，`Disabled:` 表示校验失败等原因导致未成功应用。

插件只修改进程内数据。退出游戏后替换回旧 ASI，或移走 `DS2NoSlowMo.asi`，可恢复原版行为。

## 慢动作定位

用户观察、实测结果和后续测试步骤见 [慢动作测试计划](docs/slow-motion-testing.md)。

已定位的通用时间控制入口、运行时基线和只读诊断工具见 [时间控制定位记录](docs/time-scale-addresses.md)。

## 项目内容

本项目由 `plyrthn/ds2_sd_card_music_player` 启发而创建。
