# DS2NoSlowMo

《死亡搁浅 2》目标是禁用击杀/击倒触发的慢动作。

## 开发

```powershell
.\do_build.bat Debug
.\do_build.bat Release
```

默认构建 Release。产物分别位于 `build/Debug/` 和 `build/Release/`。
完整环境配置、安装及调试步骤见 [do_build.md](do_build.md)。

## 加载验证

退出游戏，将构建出的 `DS2NoSlowMo.asi` 与 x64 ASI Loader 的 `version.dll` 放到 `DS2.exe` 同一目录，再通过 Steam 启动游戏。

日志还会记录 PID、插件版本、进程路径和插件路径。核对这些信息后，才能确认加载到了实际游戏进程。

## 慢动作定位

当前只验证 ASI 加载。用户观察、待解决的问题和后续测试步骤见 [慢动作测试计划](docs/slow-motion-testing.md)。

## 项目内容

本项目由 `plyrthn/ds2_sd_card_music_player` 启发而创建。
