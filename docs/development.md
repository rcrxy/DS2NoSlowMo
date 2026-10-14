# 构建、调试与打包

## 开发环境

编译需要 Windows x64、Visual Studio C++ x64/x86 工具链及 Windows SDK。项目使用 C++17，不依赖额外 Hook 库；SHA256 校验调用 Windows BCrypt。

VS Code 配置采用以下已验证的本机环境：

| 项目 | 配置 |
| --- | --- |
| Visual Studio | VS2026，安装目录 `C:/Software/Microsoft Visual Studio/18` |
| MSVC | `14.51.36231` |
| Windows SDK | `10.0.26100.0` |
| VS Code 扩展 | `ms-vscode.cpptools` |

在其他电脑上使用时，按实际安装位置调整 [c_cpp_properties.json](../.vscode/c_cpp_properties.json) 的 `compilerPath` 和 `windowsSdkVersion`。IntelliSense 配置不决定构建脚本选择的工具链。

## 编译

在项目根目录执行：

```powershell
.\do_build.bat Debug
.\do_build.bat Release
```

不传参数时构建 Release。脚本使用 Visual Studio Installer 的 `vswhere.exe` 查找带 C++ 工具链的安装，再调用 `vcvars64.bat`。

| 配置 | 产物 | 主要选项 |
| --- | --- | --- |
| Debug | `build/Debug/DS2NoSlowMo.asi` | `/Od /MTd /D_DEBUG` |
| Release | `build/Release/DS2NoSlowMo.asi` | `/O2 /MT /DNDEBUG` |

两种配置均启用 `/W4 /WX`。静态链接 CRT，保留调试符号；独立 PDB 不随发布包分发。

VS Code 中可使用任务 `Build ASI (Debug)` 或 `Build ASI (Release)`。默认构建任务为 Debug。

## 游戏中加载与调试

1. 完整退出游戏。
2. 将构建出的 ASI 和 INI 放到 `DS2.exe` 所在目录，按 [安装说明](../README.md#安装) 配置 ASI Loader。
3. 通过 Steam 启动游戏，检查新生成的日志。
4. 调试时使用 Debug ASI，在 VS Code 选择 `Attach to DS2 (Debug ASI)`，通过进程选择器选中实际游戏进程。

调试配置从 `build/Debug` 查找符号，并要求源码匹配。附加调试器不等于插件加载成功，加载结果应以日志和运行时检查为准。

INI 只在初始化时读取；替换 ASI 或修改开关后均需完整重启。插件仅修改进程内数据及指令。

## 源码职责

| 文件 | 职责 |
| --- | --- |
| `src/ds2_no_slowmo.cpp` | DLL 入口、初始化线程、路径和日志、INI 开关 |
| `src/time_scale_patch.h` | 游戏哈希校验、时间参数与曲线验证、两项倍率修改 |
| `src/bt_vehicle_patch.h` | BT 载具分支校验、单字节指令修改、缓存刷新及页面保护恢复 |
| `DS2NoSlowMo.ini` | 三项独立功能的默认配置 |
| `tools/analyze_timescale.py` | 离线 PE、RTTI 与反汇编分析 |
| `tools/probe_timescale.py` | 时间控制对象、参数与活动曲线的只读采样 |
| `tools/probe_bt_vehicle.py` | BT 遭遇状态和资源的只读采样 |

入口在 `DllMain` 中启动工作线程，不等待初始化结束。载具补丁先应用，曲线补丁随后等待资源和空闲请求数组，最多等待 10 分钟。

## 分析工具依赖

运行时采样工具需要 Windows 上的 64 位 Python，使用标准库和 Windows API。离线分析工具还需要 Capstone；工具从 `build/analysis/deps` 加载本地依赖。

当前使用的安装包版本为 `capstone==5.0.9`。准备该依赖：

```powershell
python -m pip install --target build/analysis/deps capstone==5.0.9
```

采样命令和手动验证流程见 [验证说明](slow-motion-testing.md)。这些开发依赖不需要随 Mod 分发。

离线分析时指定实际游戏文件：

```powershell
$ds2Executable = Read-Host 'DS2.exe 的完整路径'
python tools/analyze_timescale.py --game $ds2Executable --output build/analysis/static-evidence.json
```

输出包含 RTTI 字段、过程反汇编、入口字节、RVA 和展开信息。文件构建不匹配时工具停止分析。

## 发布包

发布包使用 Release ASI，并包含以下四个文件：

```text
DS2NoSlowMo.asi
DS2NoSlowMo.ini
README.md
LICENSE
```

包内 README 来自 [release-readme.md](release-readme.md)。[N 网页面说明](nexus-description.md) 用于发布页面，项目根 README 用于仓库。

打包后检查：

- ASI 与已验证的 Release 构建一致，版本与说明一致。
- ZIP 中仅包含上述四个文件，文件可解压且内容完整。
- INI 三个键名与源码一致，默认值均为 `1`。
- 安装说明列出独立的 x64 ASI Loader 依赖。
- LICENSE 中的作者和原有版权声明完整保留。

当前发布包位于 `build/releases/DS2NoSlowMo-0.5.0-test.zip`；同目录的 manifest 保存 ZIP 和各文件的 SHA256。只修改发布说明时更新 ZIP 与 manifest，无需重新编译 ASI。
