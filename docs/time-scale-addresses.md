# 时间倍率功能实现

本文说明人类敌人击败与物品拾取功能的数据布局、修改方式和校验要求。实现位于 `src/time_scale_patch.h`，操作步骤见 [验证说明](slow-motion-testing.md)。

## 适用构建与地址

| 项目 | 值 |
| --- | --- |
| 模块 | `DS2.exe` |
| 游戏版本 | `1.10.89.0` |
| SHA256 | `BF3D1C665545930BC850D8F5DF486F7395885BB729D4FD408FDB03390DE0765B` |
| PE 首选基址 | `0x140000000` |

本文地址均为 RVA，运行时地址为实际模块基址加 RVA。绝对对象地址和 PID 不属于可复用布局。游戏构建变化后必须重新验证文件、指令和数据。

## 修改目标

| 功能 | 参数 Name | 参数设置 | 曲线 |
| --- | --- | --- | --- |
| 人类敌人击败 | `0x4152CF0A` | 三个常量倍率 `1.0`；TimeDuration `1.75`；两个过渡值 `0.1`；Priority `17`；IsShortSlow `0` | 世界 7 点、玩家 8 点，镜头为空 |
| 物品拾取 | `0x6ED5275D` | 三个常量倍率 `1.0`；TimeDuration `1.0`；两个过渡值 `0.1`；Priority `16`；IsShortSlow `1` | 三个字段引用同一条 4 点曲线 |

修改将目标曲线所有 `Position.Y` 及 `LowestPoint` 设为 `1.0`，保留 X、切线、请求提交、计时、ID、优先级和资源引用。拾取共享曲线只修改一次。

人类请求与单次击昏的对应关系由采样确认，击杀后的移动改善由人工对照验证。三种拾取均记录到同一请求。共享关系检查限定于当前时间参数表，不证明其他资源或其他场景不会使用这些曲线。

## 初始化和校验

1. 检查完整游戏 SHA256 和 `0xD70E80` 的运行时代码前缀。
2. 解析控制对象及参数表，等待资源可用且活动请求数组为空。
3. 按精确 Name 查找唯一参数，验证参数虚表、标量、优先级及 IsShortSlow。
4. 验证曲线类型、数量、逐点值和参数表内引用关系。
5. 仅向可读写内存写入，逐项读回；失败时尝试恢复原值并记录结果。

初始化最多等待 10 分钟，每 500 毫秒重试；每个启用功能应用一次后结束该项。一个参数分支失败不阻止另一个分支尝试。资源重载后是否需重新应用尚未验证。

## 控制对象布局

全局指针槽：`0x623E9A8`，由 `0xD70FF2` 的 RIP 相对读取确定。

| 偏移 | 内容 |
| --- | --- |
| `+0x18` | 参数数量 |
| `+0x1C` | 参数容量 |
| `+0x20` | 参数指针数组 |
| `+0x28` | 活动条目数量 |
| `+0x2C` | 活动条目容量 |
| `+0x30` | 活动条目数组 |
| `+0x40 / +0x44 / +0x48` | 世界／玩家／镜头当前倍率 |
| `+0x4C / +0x50 / +0x54` | 三个目标倍率 |

活动条目步长为 `0x88`。`+0x60` 保存 Name，`+0x64` 保存 ID；`+0x40 / +0x48 / +0x50` 为曲线引用。计时增量写入 `+0x7C`，结束判断还使用其他时间值。

## 参数类型

`DSTimeScaleControlParameter` 描述符 RVA 为 `0x4348F60`，大小 `0x70`，GetRTTI 为 `0xD708E0`。

| 字段 | 类型 | 偏移 |
| --- | --- | --- |
| Name | StringHash | `0x20` |
| TimeScale | float | `0x24` |
| PlayerTimeScale | float | `0x28` |
| CameraTimeScale | float | `0x2C` |
| TimeDuration | float | `0x30` |
| TransitionTime | float | `0x34` |
| RemoveTransitionTime | float | `0x38` |
| TimeScaleCurve | Ref_CurveResource | `0x40` |
| PlayerTimeScaleCurve | Ref_CurveResource | `0x48` |
| CameraTimeScaleCurve | Ref_CurveResource | `0x50` |
| StartSound | Ref_SoundResource | `0x58` |
| Priority | uint32 | `0x60` |
| DisableCancelByCancelAllFunction | bool | `0x64` |
| IsForEnemyDefeatedWithCloseCombat | bool | `0x65` |
| IsForEnemyDefeatedWithFarCombat | bool | `0x66` |
| NeedBlurEffect | bool | `0x67` |
| IsShortSlow | bool | `0x68` |

字段来自本机 RTTI。两个 IsForEnemyDefeated 标记在已读取的参数表中均为零，不用于识别目标。常量倍率也不等于最终倍率，存在曲线时需结合曲线求值。

## 曲线布局与原始点

`CurveResource` 大小 `0x40`，GetRTTI 为 `0x1B30D90`；CurveData 基类位于 `+0x20`。点数组头为数量、容量和数据指针；CurvePoint 步长 `0x18`，X／Y 位于点内 `0x00 / 0x04`，LowestPoint 位于资源 `+0x38`。

人类敌人曲线：

| 世界 X | 世界 Y | 玩家 X | 玩家 Y |
| --- | --- | --- | --- |
| 0 | 1 | 0 | 1 |
| 0.11 | 1 | 0.11 | 1 |
| 0.20 | 0.051 | 0.20 | 0.25 |
| 0.70 | 0.051 | 0.75 | 0.25 |
| 1.10 | 0.30 | 0.80 | 0.10 |
| 1.785 | 0.051 | 1.20 | 0.10 |
| 1.80 | 0.051 | 1.70 | 0.50 |
| — | — | 1.80 | 0.50 |

拾取共享曲线：

| X | Y |
| --- | --- |
| 0 | 0.051 |
| 0.45 | 0.051 |
| 0.55 | 1 |
| 1 | 1 |

上述点的 InTangent／OutTangent 为 `0`，InTangentX／OutTangentX 为 `1`。十进制表用于阅读，实际精确比较以源码中的 float 常量为准。

## 时间控制过程

下表为反汇编得到的用途描述，未恢复原始函数名。

| RVA | 用途 |
| --- | --- |
| `0xD70FE0` | 按 Name 查找参数并调用参数读取过程 |
| `0xD70E80` | 读取参数、构造请求并提交 |
| `0xD712D0` | 添加请求，或更新同 Name 条目的计时 |
| `0xD71E60` | 更新活动请求、曲线与过渡，计算倍率 |
| `0xD71860` | 按 Name 查询活动 ID |
| `0xD717A0` | 修改结束相关值及退出过渡值 |
| `0x1089C20` | 包含拾取请求 `0x6ED5275D` 的提交路径 |

`0xD712D0` 匹配已有 Name 时清零条目 `+0x7C` 并更新 `+0x80`，存在重新计时路径；尚未直接追踪连续击杀是否执行该分支。

`0xD712D0` 的展开信息分为七段，离线工具通过 UNW_FLAG_CHAININFO 合并，不能把单段当成完整过程。

## 慢动作管理器

已注册的 `SlowMotionManager::sExportedIsGameInSlowMotion` 回调位于 `0x724530`，读取链为：

```text
DS2.exe+0x623E338 -> 根对象
根对象+0x5D0     -> 管理器
管理器+0x20     -> 判断倍率是否小于 1.0
```

管理器数组头位于 `+0x10`，数据指针位于 `+0x18`，条目步长为 `0x1C`。输出位于管理器 `+0x20 / +0x24` 和根对象 `+0x1D8 / +0x1DC`。

| RVA | 用途 |
| --- | --- |
| `0x7237E0` | 添加请求 |
| `0x723A70` | 按 ID 更新倍率 |
| `0x723BE0` | 移除或渐退请求 |
| `0x724010` | 更新请求并计算输出 |
| `0x724530` | 慢动作状态判断 |

该管理器也由时间控制更新过程调用。两条读取路径存在代码关联，不能由一次输出不变推断它们互相独立。

## 分析和验证

`tools/analyze_timescale.py` 输出 RTTI 字段、代码前缀、RVA、反汇编及展开信息；用法见 [开发说明](development.md)。

`tools/probe_timescale.py` 检查参数类型并采集当前倍率、目标倍率、活动请求和管理器输出。已验证的击昏与隐生虫修改后采样仍记录到原请求，监测倍率均为 `1.0`。这不等于所有敌人类型、局部动画速度或触发方式已覆盖。

## 参考

- [Odradek DS2 类型定义](https://github.com/ShadelessFox/odradek/blob/master/odradek-game-ds2/src/main/resources/types.json)：字段核对资料，以本机程序为准。
- [Decima RTTI 参考头文件](https://github.com/ShadelessFox/decima-native/blob/hfw-injector/source/Decima/Core/RTTI.h)：布局不能直接推广到本构建。
- [微软 x64 展开信息](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64)
- [Capstone Python API](https://www.capstone-engine.org/lang_python.html)
