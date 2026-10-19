# 宝可梦 Xaero 地图适配

为 Minecraft 1.16.5 / Forge 的 Xaero 大小地图增加 Pixelmon 重铸与重铸内容回迁支持，并提供中文 Windows 坐标迁移工具。这是非官方适配项目，与 Xaero96、Pixelmon 官方没有隶属关系。

**[下载公开工具包](https://github.com/dyfawa4/pixelmon-xaero-map-compat/releases/latest)** · **[详细安装与迁移教程](docs/迁移指南.md)** · [验证范围](docs/验证记录.md)

## 功能

- 在大小地图上使用宝可梦实体实际返回的精灵图，区分普通、异色和形态，不维护固定物种图片表。
- 支持回迁新增物种及自制小智皮卡丘 `CapPikachu`（编号 1026）；普通／异色已有专项图标验证。
- 显示究极异洞图标，隔离当前世界、地图所选维度和断线状态。
- 处理已测版本探险家指南针的 `ENCHANT_COLORS` 旧接口冲突，并避免自然罗盘与探险家指南针同时持有时的 HUD 重叠。
- 从 JourneyMap 导入普通坐标点和历史死亡点，支持中文名称、启用状态、维度对应、预览、去重、备份与恢复。

**当前不转换已探索地形。** 原 `journeymap` 数据目录保持完整。雷达范围仍受客户端同步、分类配置和服务器规则限制。

## 版本组合

| 组件 | 已测版本 |
| --- | --- |
| Minecraft / Forge / 游戏 Java | 1.16.5 / 36.2.42 / Java 11 |
| Xaero 小地图 | 26.6.0，Forge 完整雷达版 |
| Xaero 世界地图 | 1.47.0，Forge |
| XaeroLib | 1.7.3，Forge |
| Pixelmon 本体 | 内部版本 9.1.12，本机输入文件名标为 9.1.13 |
| 重铸内容回迁 | 本轮主要基线 1.5.0；早期地图回归另含 1.4.4 |
| JourneyMap 坐标点 | 5.8.6 的单点 JSON |

公开版本 `v0.1.0` 对应地图构建 `0.1.0-dev3`、桌面工具 `1.0.0`。其他版本组合和复杂多人子世界未全部实机覆盖。

## 给玩家的使用步骤

1. 下载 Release 中的 `Pixelmon-Xaero-Tools-v0.1.0.zip` 并解压，双击 `地图坐标迁移.exe`。转换器不需要 Python。
2. 点击“安装 / 生成宝可梦地图组件…”，选择 Java 11+ 和独立输出目录。已有三个固定版本的官方原文件时，可选其目录离线生成；留空则从作者官方 Modrinth 文件下载并校验。
3. 完全退出游戏，将生成的两个定制地图 JAR 和 XaeroLib 放入实例 `mods`，移走旧地图组件与 JourneyMap JAR；保留 Pixelmon、回迁模组及原 `journeymap` 数据目录。
4. 进入目标存档或服务器一次，然后退出游戏，让 Xaero 创建对应数据目录。
5. 打开转换器，选择旅行地图来源与 Xaero 目标，核对维度／子世界，预览后导入。
6. 进入游戏，在默认路径点分组核对。重复导入会去重；需要撤销时使用转换器内的备份恢复入口。

目录如何选择、版本隔离、死亡点、多个子世界及恢复限制，都在 **[迁移指南](docs/迁移指南.md)** 中逐步说明。

图标默认大小是 Xaero 原生的一半。退出游戏后可编辑 `config/xaero-pixelmon.properties`：

```properties
alwaysShowSprites=true
spriteScale=0.5
```

`spriteScale` 范围为 0.2—2.0，重启后生效。

## 公开包为何提供生成器

原版 Xaero 组件的 JAR 声明 `All Rights Reserved`。本仓库和公开附件只包含本项目原创适配逻辑、转换器、构建工具及按许可附带的 ASM；不公开打包上游完整修改版 JAR、反编译源码、Minecraft／Pixelmon 资源或玩家数据。

生成器读取作者发布的确切版本，验证 SHA-256，在玩家本地生成两个定制原生组件；**不需要额外安装独立兼容模组**。本地生成结果与验收版本的哈希完全一致。坐标转换始终可离线使用；已有官方原文件时，地图组件生成也可以离线完成。

上游作者及原许可保持不变：[Xaero 小地图](https://modrinth.com/mod/xaeros-minimap)、[Xaero 世界地图](https://modrinth.com/mod/xaeros-world-map)、[XaeroLib](https://modrinth.com/mod/xaerolib)。

## 开发与许可证

- `src/`、`resources/`、`tools/NativePatcher.java`：并入原生组件的原创适配代码。
- `migration/`：标准库转换核心与 Tk 中文界面。
- `installer/`：固定版本下载、校验及本地组件生成。
- `config/`：原版输入、输出及发布适配资源包的固定哈希。
- `tests/test_migration.py`：不启动游戏的转换回归；GitHub Actions 覆盖 Windows 与 Linux。

```powershell
python -X utf8 tests/test_migration.py
```

桌面工具重建及原生组件编译见 [开发说明](docs/开发说明.md)。原创代码与文档采用 [MIT](LICENSE)，第三方组件保留各自许可；本项目不重新授权上游代码。
