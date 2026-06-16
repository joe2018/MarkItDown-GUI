# MarkItDown GUI

桌面端 GUI,包装 [markitdown](https://github.com/microsoft/markitdown) 核心库,提供 Material 3 风格的现代化界面,把各种文件(PDF / Word / Excel / PPT / 图片 / 音频 / ...)转成 Markdown。

- **个人 / 朋友使用**:非技术朋友开箱即用
- **保留云端能力**:Azure Document Intelligence、Azure Content Understanding、LLM 视觉描述,均在「设置」页配置
- **本地优先**:本地转换无网络请求;云端功能按需启用
- **密钥安全**:API key 存 OS 钥匙串(Win Credential Manager / macOS Keychain)

## 技术栈

| 组件 | 选择 |
|------|------|
| 框架 | Flet 0.28 (Material 3, Python+Flutter) |
| 核心 | markitdown ≥ 0.1.6 |
| 密钥存储 | keyring + cryptography 加密 JSON 降级 |
| 路径 | platformdirs |
| 打包 | flet pack (PyInstaller 内核) |

## 平台支持

| 平台 | 状态 |
|------|------|
| Windows 10 / 11 | ✅ |
| macOS 12+ | ✅ |
| Linux | ❌ v1 不支持 |

## 快速开始(开发模式)

```sh
# Windows
cd packages\markitdown-gui
scripts\dev_run.bat

# macOS / Linux
cd packages/markitdown-gui
./scripts/dev_run.sh
```

第一次运行会:
1. 把兄弟包 `markitdown[all]` 装到当前 venv(可编辑模式)
2. 把 `markitdown-gui` 自己装到 venv(可编辑模式 + dev extras)
3. 启动 Flet 桌面应用

## 打包发布(给朋友用)

```sh
# Windows — 产出 dist\MarkItDown\MarkItDown.exe
scripts\build_windows.bat

# macOS — 产出 dist/MarkItDown.app
./scripts/build_macos.sh
```

打包前需要:
- `assets/icon.png`(256×256 PNG) — Windows 用
- `assets/icon.icns` — macOS 用(可用 `iconutil` 从 `.iconset` 生成)

把整个 `dist\MarkItDown\` 目录(或 `.app`)发给朋友即可。无需安装 Python 环境。

## 使用流程

1. **拖入文件** — 主页拖放区接受文件(或点击「选择文件」)
2. **开始转换** — 任务列表中点「开始转换」,后台并发 2 个
3. **查看预览** — 完成后点「预览」查看 markdown
4. **保存 / 复制** — 预览面板可复制或另存为

**配置云端服务**(可选):
1. 侧边栏点「设置」
2. 填入 LLM / Doc Intel / CU 的 endpoint + API key
3. 点「测试连接」验证
4. 保存(API key 存钥匙串)

**插件管理**:侧边栏「插件」可看到已安装的 markitdown 插件,逐一启/禁。

## 项目结构

```
packages/markitdown-gui/
├── pyproject.toml              # 依赖、版本、build 配置
├── src/markitdown_gui/
│   ├── __main__.py             # python -m markitdown_gui 入口
│   ├── app.py                  # Flet 应用根、导航
│   ├── theme.py                # Material 3 主题常量
│   ├── i18n.py                 # 中文字符串(单点源)
│   ├── models/                 # AppConfig / Job / PluginInfo
│   ├── services/               # 业务逻辑(无 UI 依赖)
│   │   ├── paths_service.py    # 用户数据目录
│   │   ├── settings_service.py # keyring + JSON + build_markitdown
│   │   ├── converter_service.py# 线程池 + 进度 + 取消
│   │   └── plugin_service.py   # 插件发现
│   ├── views/                  # Flet 页面
│   │   ├── home_view.py
│   │   ├── settings_view.py
│   │   ├── plugins_view.py
│   │   └── about_view.py
│   └── components/             # 可复用控件
│       ├── drop_zone.py
│       ├── file_list.py
│       ├── job_card.py
│       ├── key_input.py
│       ├── preview_panel.py
│       └── status_icon.py
├── tests/                      # 单元测试
└── scripts/                    # dev / build 脚本
```

## 运行测试

```sh
cd packages/markitdown-gui
pip install -e ".[dev]"
pytest
```

测试覆盖:
- `test_paths_service.py` — 用户数据目录
- `test_settings_service.py` — 配置读写、keyring CRUD、`build_markitdown()`

## 当前进度

- [x] **Phase 1**: 项目骨架、pyproject、Flet 应用外壳
- [x] **Phase 2**: 路径服务、设置服务(keyring + JSON + 降级)
- [x] **Phase 3**: 主页(拖放/队列/预览) + 转换服务(线程池/取消)
- [x] **Phase 4**: 设置页(LLM / Doc Intel / CU / 测试连接)
- [x] **Phase 5**: 插件页 + 关于页
- [x] **Phase 6**: 打包脚本(Win / macOS)
- [ ] **v1.1**: 用户密码 prompt、dragged-drop 优化、错误日志持久化

## 已知限制

- `enable_plugins` 是统一开关;per-plugin 控制通过 `build_markitdown()` 中过滤 `_converters` 实现
- Doc Intel 没有轻量健康检查,只能验证 endpoint 可达 + 客户端构造
- keyring 不可用时,降级到**进程级**密码加密的本地文件;跨重启不能读回(v1.1 改用用户密码)
- macOS Gatekeeper 首次启动需右键「打开」绕过;v1 不公证
- 朋友电脑需要 ffmpeg / exiftool(Windows 安装包会捆绑 .exe)

## 许可

MIT,继承自 markitdown 主体仓库。
