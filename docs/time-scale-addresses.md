# 时间控制定位记录

分析日期：2026-10-14。记录文件分析、运行时读取证据和定向测试版；修改后的两次击昏采样确认已监测的倍率减速消失，其他覆盖范围仍待验证。

## 版本与地址使用条件

- 模块：`DS2.exe`，文件版本 `1.10.89.0`。
- SHA256：`BF3D1C665545930BC850D8F5DF486F7395885BB729D4FD408FDB03390DE0765B`。
- PE 首选基址：`0x140000000`。反汇编中的 `0x140...` 地址不是本次运行时地址。
- 下表使用 RVA；运行时地址必须是实际模块基址加 RVA。
- 游戏更新后不能继续沿用这些地址。工具先校验文件哈希和运行时入口字节，校验失败即停止。

## 已定位的通用时间控制代码

下列用途是根据反汇编描述的功能，不是恢复出来的原始函数名称。

| 模块相对位置 | 静态证据 | 运行时验证状态 |
| --- | --- | --- |
| `DS2.exe+0xD70FE0` | 按 `Name` 哈希查参数表，然后调用 `0xD70E80` | 对象和参数表已读到；事件调用尚未追踪 |
| `DS2.exe+0xD70E80` | 从 `RDX` 指向的参数对象读取倍率、持续时间、过渡时间及曲线，构造请求后调用 `0xD712D0` | 入口字节与磁盘一致；事件调用尚未追踪 |
| `DS2.exe+0xD712D0` | 操作活动请求数组；匹配到已有 `Name` 值时，清零已有条目的计时值并更新另一个时间值 | 入口字节与磁盘一致；击杀是否走此分支尚未验证 |
| `DS2.exe+0xD71E60` | 遍历活动条目，增加计时、计算曲线及过渡、移除结束条目，并更新三个倍率输出 | 入口字节与磁盘一致；输出的正常状态基线已读取 |
| `DS2.exe+0xD71860` | 按 `Name` 值查找活动条目并返回其 ID 值 | 尚未采集事件调用 |
| `DS2.exe+0xD717A0` | 修改指定活动条目的结束相关值和退出过渡值 | 尚未采集事件调用 |
| `DS2.exe+0x623E9A8` | 保存时间控制对象指针的全局位置，由 `0xD70FF2` 的 RIP 相对读取指令确定 | 已读到非零对象、80 个参数及正常倍率值 |

`0xD712D0` 的 `.pdata` 记录分成七段，通过 `UNW_FLAG_CHAININFO` 关联到同一个入口。不能把其中的单段范围当作完整函数。分析工具已按链式展开信息合并这些记录。

## 慢动作管理器路径

在 `DS2.exe+0x723740` 中，注册字符串 `SlowMotionManager::sExportedIsGameInSlowMotion` 对应的回调地址为 `DS2.exe+0x724530`。该回调的完整代码直接验证了以下读取链：

```text
DS2.exe+0x623E338 -> 根对象
根对象+0x5D0     -> 慢动作管理器
管理器+0x20     -> 与 1.0 比较的浮点值
```

任一对象为空时返回假；比较值小于 `1.0` 时返回真。这里没有通过字符串相似性推断注册关系，而是读取了注册函数传入的实际回调地址。

| 模块相对位置 | 反汇编证据 |
| --- | --- |
| `DS2.exe+0x7237E0` | 添加一条请求，数组步长 `0x1C`，返回 ID |
| `DS2.exe+0x723A70` | 按 ID 更新请求的两个倍率；ID 不存在时调用添加函数 |
| `DS2.exe+0x723BE0` | 按 ID 移除请求，或将目标倍率设回 `1.0` 并计算退出变化率 |
| `DS2.exe+0x724010` | 更新请求内的倍率变化，计算最小倍率并写管理器 `+0x20`、`+0x24` |
| `DS2.exe+0x724530` | 上述已注册的慢动作判断回调 |

管理器的数组数量位于 `+0x10`，容量位于 `+0x14`，数据指针位于 `+0x18`。条目首个 32 位值是 ID，后续六个浮点值按偏移原样记录。更新函数还写入根对象 `+0x1D8`、`+0x1DC`；此处仍使用偏移表示，未恢复字段原名。

暂停时的只读验证：根对象 `0x4C10946C400`，管理器 `0x4C12F22C6C0`，请求数零，上述四个浮点输出均为 `1.0`。入口字节与磁盘一致。原始记录：`build/analysis/paused-two-controllers.json`。

这一管理器也被此前的 `0xD71E60` 调用，因此两条路径存在代码关联；不能把一次采样未变化解释成两套完全独立的系统。具体战斗事件的调用关系仍需采样验证。

## 参数类型与字段

本机 RTTI 的字段名、类型、偏移及标记已逐条与 Odradek 的 DS2 类型导出核对。

- 类型：`DSTimeScaleControlParameter`。
- 类型描述符 RVA：`0x4348F60`。
- 对象大小：`0x70`。
- `GetRTTI` 代码 RVA：`0xD708E0`；构造函数使用的虚表首项也指向此位置。

| 字段名称 | 类型 | 对象内偏移 |
| --- | --- | --- |
| `Name` | `StringHash` | `0x20` |
| `TimeScale` | `float` | `0x24` |
| `PlayerTimeScale` | `float` | `0x28` |
| `CameraTimeScale` | `float` | `0x2C` |
| `TimeDuration` | `float` | `0x30` |
| `TransitionTime` | `float` | `0x34` |
| `RemoveTransitionTime` | `float` | `0x38` |
| `TimeScaleCurve` | `Ref_CurveResource` | `0x40` |
| `PlayerTimeScaleCurve` | `Ref_CurveResource` | `0x48` |
| `CameraTimeScaleCurve` | `Ref_CurveResource` | `0x50` |
| `StartSound` | `Ref_SoundResource` | `0x58` |
| `Priority` | `uint32` | `0x60` |
| `DisableCancelByCancelAllFunction` | `bool` | `0x64` |
| `IsForEnemyDefeatedWithCloseCombat` | `bool` | `0x65` |
| `IsForEnemyDefeatedWithFarCombat` | `bool` | `0x66` |
| `NeedBlurEffect` | `bool` | `0x67` |
| `IsShortSlow` | `bool` | `0x68` |

这证明资源类型具备这些字段，不证明某个具体参数就是击杀或击昏效果。当前读取到的 80 个参数中，两个 `IsForEnemyDefeated...` 字段全部为零。不能将它们直接作为唯一过滤条件。

`TimeScale` 等常量也不能单独代表最终倍率：代码在曲线存在时计算曲线值，持续时间也会受到曲线范围影响。

另一个类型 `DSTimeScaleControlConfig` 的描述符 RVA 为 `0x43490C0`，对象大小 `0x38`，读取到以下精确字段：

| 字段名称 | 类型 | 对象内偏移 |
| --- | --- | --- |
| `ExtendTimeForSlowOfEnemyDefeated_VeryEasy` | `float` | `0x20` |
| `ExtendTimeForSlowOfEnemyDefeated_Easy` | `float` | `0x24` |
| `ExtendTimeForSlowOfEnemyDefeated_Normal` | `float` | `0x28` |
| `ExtendTimeForSlowOfEnemyDefeated_VeryHard` | `float` | `0x30` |

其值、加载位置和实际使用路径尚未确认。不能仅凭字段名称下结论。

## 正常状态基线

本次实际游戏读取：

- PID：`2784`。
- `DS2.exe` 基址：`0x7FF650C40000`。
- 时间控制对象：`0x4C0C58946E0`。
- 参数表数量：`80`。
- 活动请求数量：`0`。
- 对象内 `0x40`、`0x44`、`0x48` 三个当前倍率值均为 `1.0`；`0x4C`、`0x50`、`0x54` 三个目标值也均为 `1.0`。

这些运行时绝对地址仅适用于本次进程。后续通过模块基址及全局指针重新解析。

原始记录：`build/analysis/runtime-baseline.json`。参数对象的类型通过其虚表 `GetRTTI` 入口核对，未根据数值范围猜测类型。

## 第一轮进入战斗采样

- 开始时间：`2026-10-14 11:01:03 +08:00`。
- 采样窗口：60 秒，实际记录 5999 次，读取错误 0 次。
- 活动条目数量在所有采样中均为零。
- 六个倍率输出在所有采样中均为 `1.0`。
- 原始数据：`build/analysis/combat-entry.jsonl`；汇总：`build/analysis/combat-entry-summary.json`。

用户反馈：被敌人发现后短暂进入慢动作，未攻击、未击倒；之后暂停游戏。本轮数据没有记录到上述控制对象的变化，尚未将这个效果与该对象关联。缺少精确的事件时间标记，且轮询可能漏掉极短变化，不能据此排除该路径。

## 单次击倒实测与定向测试版

用户确认：本次只击倒一名人类敌人，出现慢动作，没有其他操作。

- 第二轮窗口 90 秒，采样间隔 5 毫秒；记录 18000 次，读取错误 0 次。
- 唯一活动请求 `Name=0x4152CF0A`，本次 ID 为 `2`。
- 请求首次／末次被读取的间隔为约 `1.789` 秒。这是本轮观测跨度，不能当作所有场景的固定时长。
- 控制对象当前世界倍率 `+0x40` 最低约 `0.051`，玩家倍率 `+0x44` 最低约 `0.10`，镜头倍率 `+0x48` 始终 `1.0`。
- 慢动作管理器 `+0x20` 最低同样约 `0.051`，`+0x24` 始终 `1.0`。
- 原始数据与汇总：`build/analysis/single-knockout.jsonl`、`build/analysis/single-knockout-summary.json`。

此参数存在于 80 项参数表中：`TimeScale`、`PlayerTimeScale`、`CameraTimeScale` 都为 `1.0`，`TimeDuration=1.75`，两个过渡值约 `0.1`，`Priority=17`。两个击败标记均为零。世界和玩家曲线非空，镜头曲线为空。

本机 RTTI 与读取类型校验确定：`CurveResource` 大小 `0x40`，`CurveData` 基类偏移 `0x20`，`CurvePoint` 步长 `0x18`；`Position.X` 位于点内 `0`，`Position.Y` 位于 `4`。虚表的 `GetRTTI` 入口为 `DS2.exe+0x1B30D90`。

实际曲线点（浮点数在表中作十进制舍入）：

| 世界曲线 X | 世界曲线 Y | 玩家曲线 X | 玩家曲线 Y |
| --- | --- | --- | --- |
| 0 | 1 | 0 | 1 |
| 0.11 | 1 | 0.11 | 1 |
| 0.20 | 0.051 | 0.20 | 0.25 |
| 0.70 | 0.051 | 0.75 | 0.25 |
| 1.10 | 0.30 | 0.80 | 0.10 |
| 1.785 | 0.051 | 1.20 | 0.10 |
| 1.80 | 0.051 | 1.70 | 0.50 |
| — | — | 1.80 | 0.50 |

曲线原始记录：`build/analysis/knockout-curves.json`。在读取的参数表中，仅该参数引用这两条曲线；这不是对所有已加载和未加载资源的共享关系证明。

`0.2.0-test` 采用资源曲线修改：只在已支持的游戏哈希、运行时入口字节、参数虚表、标量设置、逐个曲线点及参数表内引用检查通过、活动请求数组为空时，把这 15 个点的 Y 和两个 `LowestPoint` 改为 `1.0`。保留 X、切线、请求、计时、ID 和资源引用。写入限于可读写内存，逐项读回验证；写入失败时尝试恢复原值并记录结果。

该版在启动后最多等待 10 分钟，成功应用一次即结束初始化线程。不修改磁盘游戏文件，不注入 Hook。重新加载资源是否需要重新应用，尚待测试。该请求是否也被其他触发场景使用、不同击倒方式是否使用相同请求，尚未验证。

Release 构建通过 `/W4 /WX`。单独执行 SHA256 校验代码确认接受实际游戏、拒绝其他文件。旧 ASI 和日志备份至 `build/rollback/20261014-111800/`，部署记录为 `build/knockout-deployment.json`。

重启后 PID `23776` 的日志确认 `Applied: Name=0x4152CF0A`；独立只读工具确认世界 7 点、玩家 8 点均为 `1.0`，两个 `LowestPoint` 也为 `1.0`，参数标量设置未改变。记录：`build/analysis/patched-curves.json`。

### 修改后的游戏验证

| 测试 | 样本数 | 读取错误 | 活动请求 | 已监测的倍率 | 用户反馈 |
| --- | --- | --- | --- | --- | --- |
| 单次击昏 | 18000 | 0 | `0x4152CF0A` | 全程 `1.0` | 音效仍在，体感似乎变弱 |
| 再次击昏 | 14999 | 0 | `0x4152CF0A` | 全程 `1.0` | 能感到镜头特效，操作延迟好像没了 |

“已监测的倍率”指控制对象的六个输出、慢动作管理器的两个输出，以及根对象 `+0x1D8`、`+0x1DC`。两次请求仍按原有计时存在，原来的 `0.051`／`0.10` 倍率变化不再出现。因此当前结论是本次已验证请求的倍率减速已取消；不能据此宣称所有非致命方式、所有敌人类型或所有动画局部速度均已覆盖。音效与镜头视觉反馈未处理。

原始采样及汇总：`build/analysis/patched-single-knockout.jsonl`、`build/analysis/patched-single-knockout-summary.json`、`build/analysis/patched-repeat-knockout.jsonl`、`build/analysis/patched-repeat-knockout-summary.json`。

之后用户自行清理区域，反馈击杀后 Sam 的动作停顿明显改善，但仍有极短时停感，来源未确定；该轮未同步采样，不能据此认定击杀一定使用同一请求或所有敌人动画已正常。从隐匿转为被发现时稳定触发的遇敌时停单独记录，不纳入当前修改范围。

为进行 A/B 对照，用户退出游戏后，把当前 `0.2.0-test` ASI 移至 `build/ab-test/20261014-115153/DS2NoSlowMo.asi`，哈希验证通过；Loader 保持不变。用户完成无 Mod 对照反馈：原版有明显约 1～2 秒的时停体感，瞄准不受影响，但严重妨碍 Sam 的移动指令；期间再次击杀会重置时停。这一轮没有同步内存记录，属于用户观察。

上述时间范围与此前单次击昏的活动跨度接近，但不能据此证明击杀使用同一参数或重置分支。结合修改后倍率始终为 `1.0` 的两次击昏记录，A/B 反馈支持当前修改显著改善移动受阻；极短残留体感及所有击杀／击昏方式的覆盖范围仍待确认。

对照完成并确认 DS2 退出后，已将同一个测试版复制回游戏目录，校验 SHA256 与备份一致；备份继续保留，未修改源码或重新构建。`build/ab-test-state.json` 当前为 `restored`。

恢复后用户再次反馈：战斗更舒适；遇敌时停期间快速击倒该敌人，会使遇敌减速表现提前结束。未同步采样，也没有对应的无 Mod 交互对照。现有源码只修改击倒曲线，保留请求提交和计时流程；这条观察不能证明遇敌请求被取消，或该交互由 Mod 引入。后续若研究，应同时记录两种请求及最终倍率。当前不增加遇敌效果的修改。

回退：正常退出游戏，将 `build/rollback/20261014-111800/DS2NoSlowMo.asi` 复制回游戏目录覆盖测试版；或移走游戏目录中的 `DS2NoSlowMo.asi`。曲线修改仅存在于进程内，不保存到游戏程序或存档中。

## 活动条目和重新计时路径

静态代码证明时间控制对象内有：

- `+0x18`：参数表数量。
- `+0x20`：参数指针数组。
- `+0x28`：活动条目数量。
- `+0x30`：活动条目数组。
- 活动条目步长：`0x88`。

在活动条目内，代码比较 `+0x60` 的 `Name` 值，ID 值存放在 `+0x64`。更新函数把时间增量加到 `+0x7C`，再与其他时间值组合比较以决定是否结束条目。

`0xD712D0` 匹配到已有条目时，包含如下指令：

```asm
DS2.exe+0xD714A2  mov     dword ptr [rcx+r9+0x7C], 0
DS2.exe+0xD714AF  vmovss  xmm0, dword ptr [rbx+0x20]
DS2.exe+0xD714B4  vaddss  xmm1, xmm0, dword ptr [rbx+0x0C]
DS2.exe+0xD714B9  vmovss  dword ptr [rcx+rax+0x80], xmm1
```

因此该通用系统存在重新计时的路径。用户在无 Mod 对照中已观察到连续击杀重置时停；是否实际执行此分支、具体请求及额外限制，仍需同步采样或断点记录确认。

## 复现工具

### 离线分析

```powershell
python tools\analyze_timescale.py --game 'D:\SteamLibrary\steamapps\common\DEATH STRANDING 2 - ON THE BEACH\DS2.exe'
```

输出：`build/analysis/static-evidence.json`，包含 11 个类型记录、12 个完整过程及慢动作判断回调的反汇编、入口字节、RVA 和展开信息范围。

工具使用本地 `build/analysis/deps` 中的 Capstone。此次从 PyPI 下载并校验了 `capstone-5.0.9-py3-none-win_amd64.whl`，未安装到全局 Python 环境；该包的 Python 绑定报告版本字符串为 `5.0.7`。新环境需要先准备这一开发分析依赖。

### 只读运行时快照

```powershell
python tools\probe_timescale.py --output build\analysis\runtime-snapshot.json
```

工具只通过 Tool Help 枚举模块和 `ReadProcessMemory` 读取数据。不注入、不调用游戏函数、不冻结值、不申请进程内存写权限。

当前沙箱拒绝对游戏进程枚举模块，因此实际读取在已授权的沙箱外执行。若其他环境返回访问拒绝，需要确认进程权限，不能据此推断游戏存在保护机制。

### 连续采样

```powershell
python tools\probe_timescale.py --watch 45 --interval 0.01 --output build\analysis\combat-entry.jsonl
```

采样前先读取基线并校验版本，然后同时记录时间控制对象的三个当前倍率、三个目标值、活动条目，以及慢动作管理器的倍率、请求条目和根对象输出。这里的 `0.01` 是人为选择的采样间隔，不是游戏效果持续时间。

快照是顺序读取，不能保证所有浮点值处于同一瞬间。数组结构发生变化时记录读取错误；轮询也可能漏掉短于采样窗口的变化。极短时停仍可能需要后续写入断点或插桩确认。

## 尚未完成

1. 将一次单独的“进入战斗”与具体活动请求关联。
2. 验证定向测试版是否消除实际击倒／击昏慢动作，并确认不同方式的覆盖范围。
3. 重复单次击昏及连续击昏，验证该请求的触发范围和重新计时行为。
4. 后续才考虑击杀；其他触发场景暂不处理。
5. 检查重载存档或场景是否重建参数与曲线；当前版只应用一次。

当前 ASI 为定向曲线修改测试版，不强制夹取通用时间倍率。

## 配置开关与拾取效果定位阶段

用户选择 INI 开关，重启生效，并指定优先处理电气虫／隐生虫拾取时停。`0.3.0-test` 新增 `[Features] DisableHumanDefeatSlowMo=1`，读取 ASI 同目录的 `DS2NoSlowMo.ini`；设 `0` 时跳过原来的曲线修改，缺省为 `1`，非法值停止应用并记录原因。原有游戏数据修改逻辑未变。

Release 编译及本地加载分支验证通过，已部署 ASI 与 INI，哈希核对通过。旧版备份：`build/rollback/config-20261014-121501/`。当前只提供已实现功能的开关，拾取参数尚未关联，不添加尚未生效的拾取配置项。

拾取定位先分别记录两类虫的单次事件，再观察短间隔重复拾取。使用现有两个时间控制对象的只读采样；在记录到实际请求或管理器变化前，不指定拾取请求哈希。遇敌／BT 暂不修改。

### 拾取共享请求的实测证据

`0.3.0-test` 下分别单独拾取隐生虫、电气虫和开罗尔晶体，都记录到唯一活动请求 `Name=0x6ED5275D`。三轮样本数分别为 11993、12000、11997，读取错误均为零；活动跨度分别约 0.985、0.990、0.985 秒，世界／玩家／镜头最低倍率均约 `0.051`。这是本次事件和请求的关联，不证明请求只用于这些场景。

实际参数：三个常量倍率均为 `1.0`，`TimeDuration=1.0`，两个过渡值约 `0.1`，`Priority=16`，`IsShortSlow=1`；三个曲线字段引用同一 `CurveResource`。四个点的 `Position` 为 `(0, 0.051)`、`(0.45, 0.051)`、`(0.55, 1)`、`(1, 1)`，四点的 In／OutTangent 均为 `0`，In／OutTangentX 均为 `1`。当前 80 项参数表中，没有其他参数引用这条曲线。

精确哈希字节搜索定位到 `DS2.exe+0x1089D8C`：

```asm
DS2.exe+0x1089D84  lea rdx, [rsp+0x90]
DS2.exe+0x1089D8C  mov dword ptr [rsp+0x90], 0x6ED5275D
DS2.exe+0x1089D97  call DS2.exe+0xD70FE0
```

所在过程入口 `DS2.exe+0x1089C20`，未恢复原名。上游读取两个计时对象，并在 `0x1089D3B` 与浮点常量 `2.0` 比较后决定是否到达请求路径；完整时间单位和其他状态条件尚未验证，不据此宣称冷却固定为 2 秒。原始反汇编：`build/analysis/bug-pickup-request-disasm.txt`，该过程已加入离线证据提取工具。

原始参数与曲线：`build/analysis/cryptobiote-curves.json`。三轮采样及汇总使用 `cryptobiote-single-pickup`、`electric-bug-single-pickup`、`chiral-crystal-single-pickup` 文件名，位于 `build/analysis/`。

### 0.4.0-test 独立开关及验证

新增 `[Features] DisablePickupSlowMo=1`，与 `DisableHumanDefeatSlowMo` 独立。每项设 `0` 即跳过，缺省为 `1`，非法值仅停止该项。配置在启动时读取，重启生效。

公共代码移至 `src/time_scale_patch.h`。原有人类敌人分支继续验证七点／八点曲线及既有参数；拾取分支验证 `0x6ED5275D`、标量设置、优先级、`IsShortSlow`、三个字段同指针、四个原始点及参数表内引用，然后只修改该共享曲线一次。保留请求、计时、优先级、标记和资源引用。一个分支校验失败不会阻止另一个已启用分支尝试应用。

Release 编译通过 `/W4 /WX`。本地宿主验证全部关闭、只开启人类敌人、只开启拾取、非法值及缺省两项开启；宿主未进入游戏修改逻辑。旧版 ASI、INI、日志备份至 `build/rollback/pickup-20261014-123733/`。部署时保留原有人类敌人配置，追加拾取项，安装前后哈希核对；记录：`build/pickup-deployment.json`。

真实游戏 PID `3108` 的 `0.4.0-test` 日志确认两个开关为 `1`、两个请求应用成功。独立读取 `build/analysis/patched-pickup-curves.json` 确认共享曲线四点和 `LowestPoint` 均为 `1.0`；`build/analysis/v04-human-defeat-curves.json` 确认原有世界七点、玩家八点仍全部为 `1.0`。

修改后用户多次拾取隐生虫，反馈没有慢动作。`build/analysis/patched-cryptobiote-pickup.jsonl` 记录 11997 次、读取错误零次，仍出现 `0x6ED5275D`，三个当前倍率全程为 `1.0`。对应汇总为 `patched-cryptobiote-pickup-summary.json`。

修改后的电气虫、晶体尚未逐项实测；请求的其他用途、重复拾取条件及资源重载后的应用情况仍待验证。两个实际游戏中的关闭分支尚未通过重启逐项采样，但本地加载已确认配置选择和跳过路径。

## 参考

- [Odradek 的 DS2 类型定义](https://github.com/ShadelessFox/odradek/blob/master/odradek-game-ds2/src/main/resources/types.json)：仅作字段核对，实际字段表仍从本机程序读取。
- [Decima RTTI 参考头文件](https://github.com/ShadelessFox/decima-native/blob/hfw-injector/source/Decima/Core/RTTI.h)：旧头文件的字段计数位置与本机版本不同，没有直接沿用。
- [微软 x64 异常处理与链式展开信息](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64)
- [Capstone Python API](https://www.capstone-engine.org/lang_python.html)
