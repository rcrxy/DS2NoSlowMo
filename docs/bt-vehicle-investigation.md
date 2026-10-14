# BT 载具功能实现

`DisableBTVehicleShutdown` 控制进入 BT 区时的载具强制熄火与操控中断。实现位于 `src/bt_vehicle_patch.h`，修改进程内的一条条件跳转；全局遭遇状态和关机／开机曲线不在修改范围内。

## 适用构建

适用于 [时间倍率实现说明](time-scale-addresses.md#适用构建与地址) 中指定的 `DS2.exe`。本文地址均为 RVA，运行时需加实际模块基址。

## 分支修改

载具更新过程 `0x1F66E10` 在 `0x1F67061` 以载具 `+0xB50` 为参数调用 `0x1F806F0`。后者读取 BT 遭遇状态，并在进入强停流程时设置自身 `+0x3C`，即载具 `+0xB8C`，随后设置载具标志、提交灯光关闭音效并调用虚函数。

入口检查：

```asm
DS2.exe+0x1F80878  cmp byte ptr [r8+0x1D], 0
DS2.exe+0x1F8087D  je DS2.exe+0x1F808BF
DS2.exe+0x1F8087F  mov byte ptr [rdx+0x3C], 1
```

补丁将 `0x1F8087D` 的 `74 40` 改为 `EB 40`，即将 je 改为 jmp。只写入第一字节，指令长度和目的地 `0x1F808BF` 不变，始终走原有返回路径。

配置为 `0` 时不修改该指令。配置在初始化时读取，需重启生效；无需 Hook 库。

## 写入校验

应用前检查：

- 完整游戏 SHA256。
- `0x1F806F0` 的 16 字节入口前缀。
- `0x1F80865` 开始的 58 字节原始指令。
- 目标页面已提交，属于主模块 MEM_IMAGE，保护为 PAGE_EXECUTE_READ。

写入时临时开放页面写权限；修改后读回并刷新指令缓存。失败时尝试恢复原字节，最后恢复原页面保护，并将结果写入日志。磁盘上的游戏可执行文件不变。

成功日志包含 `Applied: BT vehicle shutdown entry skipped`；`protection_restored=1` 表示页面保护恢复成功。

## 遭遇状态布局

全局指针槽 `0x623F9D8` 指向大小 `0x20` 的状态对象。以下为代码读写确认的用途，未恢复字段原名：

| 偏移 | 用途 |
| --- | --- |
| `+0x00` | 浮点累计值 |
| `+0x04` | 阶段浮点计时值 |
| `+0x08` | 当前状态编号 |
| `+0x0C` | 上一状态编号 |
| `+0x10` | 曲线求值结果，载具代码读取 |
| `+0x1D` | 进入载具强停分支前检查的字节 |

遭遇过程中可观测到 `0 → 1 → 2 → 3 → 0`。状态编号用于验证流程触发，不作为载具速度或控制状态的直接测量。

## 遭遇资源

| 项目 | RVA／大小 |
| --- | --- |
| 资源指针槽 | `0xA1D5CE0` |
| 更新过程 | `0x1EC9890` |
| DSGazerAreaEnterResource 描述符 | `0x44B7F80` |
| 构造虚表 | `0x33A63F8` |
| GetRTTI | `0x1EC29E0` |
| 对象大小 | `0x68` |

| 字段 | 偏移 |
| --- | --- |
| OnToOff | `+0x20` |
| OffToOn | `+0x28` |
| CameraShake0 | `+0x30` |
| CameraShake1 | `+0x38` |
| CameraRumble | `+0x40` |
| SimpleEnterSound | `+0x48` |
| OffTime | `+0x50` |
| StartChillsTimeFromOff | `+0x54` |
| EndChillsTimeFromOff | `+0x58` |
| StartCameraShakeTime0 | `+0x5C` |
| StartCameraShakeTime1 | `+0x60` |

实测 OffTime 为 `3.0`。更新代码在状态 `2` 中与此值比较，然后切换至状态 `3`。

相关音效来自 DSVehicleSoundResource 的 `GazerAreaEnterBlinkOff`、`GazerAreaEnterPowerOff` 和 `GazerAreaEnterBlinkOn`。音效注册位置可帮助定位调用路径；屏蔽音效不能代替阻止载具强停。

## 验证与限制

三轮巡航摩托实测强制停止消失，动画、警告、特效、音效和灯光正常；卡车实测无强制停止，奥卓德克正常。

摩托车同步采样确认：修改后的遭遇状态仍完整变化，OffTime 仍为 `3.0`，运行时跳转为 `EB 40`。卡车结果来自人工测试，没有同步内存采样。其他遇敌动作选项及其他载具中断事件尚未验证。

`tools/probe_bt_vehicle.py` 只读验证状态及资源，记录原始字节与偏移值，不读取载具本体、标志或速度。使用步骤见 [验证说明](slow-motion-testing.md#bt-载具)。
