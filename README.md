# DS2NoSlowMo

《死亡搁浅 2》ASI Mod，用于取消人类敌人击杀／击昏后的慢动作、物品拾取慢动作，以及进入 BT 区时的载具强制停车。三项功能可独立配置。

版本：`0.5.0-test` · 作者：`zeco` · 平台：Windows x64 / Steam

## 功能

| 功能 | 效果 |
| --- | --- |
| 人类敌人击败 | 取消击杀／击昏后的倍率减速，改善 Sam 的移动响应 |
| 物品拾取 | 取消拾取隐生虫、电气虫、开罗尔晶体时的倍率减速 |
| BT 区载具 | 取消进入 BT 区时的强制熄火与操控中断，摩托车和卡车已实测通过 |

减速取消后，原有音效与镜头反馈仍可能保留。BT 载具功能已验证奥卓德克正常播放。

## 兼容范围

当前支持已验证的 Steam 游戏构建 `1.10.89.0`。插件检查游戏文件及运行时数据；构建不匹配时停止对应修改并记录原因。其他版本、商店版本，以及修改相同资源或指令的 Mod 尚未验证。

人类敌人发现 Sam 时的慢动作、大型 BT 击败效果和其他触发场景不属于本版的实现范围。测试覆盖见 [验证说明](docs/slow-motion-testing.md)。

## 安装

1. 完整退出游戏。
2. 将 [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) 的 x64 `version.dll` 放到 `DS2.exe` 所在目录；已有可用 ASI Loader 时沿用现有配置。
3. 将 `DS2NoSlowMo.asi` 和 [DS2NoSlowMo.ini](DS2NoSlowMo.ini) 放到同一目录。
4. 通过 Steam 启动游戏。

ASI Loader 需单独安装。插件启动后在 ASI 同目录生成 `DS2NoSlowMo.log`。

## 配置

编辑 `DS2NoSlowMo.ini`：

```ini
[Features]
DisableHumanDefeatSlowMo=1
DisablePickupSlowMo=1
DisableBTVehicleShutdown=1
```

| 配置项 | 控制的功能 |
| --- | --- |
| `DisableHumanDefeatSlowMo` | 人类敌人击杀／击昏后的减速 |
| `DisablePickupSlowMo` | 三种物品拾取的减速 |
| `DisableBTVehicleShutdown` | BT 遭遇时的载具强停 |

`1` 启用对应修改，`0` 保留原效果。缺省值均为 `1`，各项互不绑定。非法值只停用该项，并写入日志。

**修改配置后需完整退出并重启游戏。**

## 排查与卸载

| 日志前缀 | 含义 |
| --- | --- |
| `Applied:` | 对应修改已应用 |
| `Skipped:` | 配置为 `0`，跳过该项 |
| `Disabled:` | 校验或访问失败，未应用该项 |

没有日志时，检查 ASI Loader 和安装目录。报告问题时请提供游戏版本、插件版本、配置、复现步骤及相关日志行。

恢复单项原效果：将其配置设为 `0` 并重启。卸载：退出游戏后移除 `DS2NoSlowMo.asi` 和 `DS2NoSlowMo.ini`；生成的日志也可删除。其他 Mod 依赖的 ASI Loader 应保留。

## 开发文档

- [构建、调试与打包](docs/development.md)
- [手动验证与只读采样](docs/slow-motion-testing.md)
- [时间倍率功能实现](docs/time-scale-addresses.md)
- [BT 载具功能实现](docs/bt-vehicle-investigation.md)
- [发布包英文说明](docs/release-readme.md)
- [N 网页面说明](docs/nexus-description.md)

## 许可与致谢

采用 [MIT License](LICENSE)，作者为 zeco，保留原有版权声明。本项目由 `plyrthn/ds2_sd_card_music_player` 启发而创建；Ultimate ASI Loader 为独立项目。
