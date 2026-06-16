"""Centralized Chinese strings.

Architecture is i18n-ready (single source of truth for all visible text),
but v1 ships Chinese only. To add English, switch this to a lookup function
keyed by `locale` and pass it through.
"""


class T:
    # --- App / nav ---
    app_title = "MarkItDown"
    nav_home = "主页"
    nav_settings = "设置"
    nav_plugins = "插件"
    nav_about = "关于"

    # --- Phase 1 placeholder ---
    placeholder_subtitle = "(占位) 后续阶段将填入实际功能"

    # --- Home view (Phase 3) ---
    home_drop_title = "拖入文件到此处"
    home_drop_subtitle = "或 点击选择文件"
    home_drop_supported = "支持 PDF / Word / Excel / PPT / HTML / EPUB / ZIP 等(暂不支持图片与音频)"
    home_tasks_title_pending = "任务列表"
    home_action_clear = "清空"
    home_action_clear_completed = "清除已完成"
    home_action_convert = "开始转换"
    home_action_cancel = "取消"
    home_action_remove = "移除"
    home_status_pending = "等待中"
    home_status_running = "转换中..."
    home_status_done = "完成"
    home_status_failed = "失败"
    home_status_cancelled = "已取消"
    home_action_preview = "预览"
    home_action_open_folder = "打开文件夹"
    home_action_retry = "重试"
    home_action_delete = "删除"
    home_action_copy_pip = "复制安装命令"
    home_action_copy = "复制全部"
    home_action_save_as = "保存为"
    home_preview_empty = "(选择一个已完成的任务以查看预览)"
    home_drop_browse = "选择文件"
    home_tasks_empty = "(尚无任务 — 拖入文件或点击上方区域)"
    home_unsupported_file = lambda ext: f"已跳过不支持的文件类型: {ext}"  # type: ignore[assignment]
    home_unsupported_audio_video = "已跳过: 暂不支持图片与音频转换"
    home_tasks_count = lambda n: f"任务列表 ({n})"  # type: ignore[assignment]

    # --- Settings view (Phase 4) ---
    settings_back = "返回"
    settings_save = "保存"
    settings_cancel = "取消"
    settings_section_llm = "LLM(图片描述 / OCR)"
    settings_section_docintel = "Azure Document Intelligence(可选)"
    settings_section_cu = "Azure Content Understanding(可选)"
    settings_section_output = "输出"
    settings_section_advanced = "高级选项"
    field_base_url = "Base URL"
    field_api_key = "API Key"
    field_model = "Model"
    field_endpoint = "Endpoint"
    field_api_version = "API 版本(可选)"
    field_analyzer = "Analyzer ID(留空=自动选择)"
    field_cu_file_types = "文件类型(逗号分隔,留空=全部)"
    field_output_dir = "默认输出目录"
    field_output_dir_same = "源文件同目录"
    field_output_dir_pick = "选择..."
    field_keep_data_uris = "保留 data URI"
    field_exiftool = "exiftool 路径"
    field_exiftool_auto = "自动检测"
    test_connection = "测试连接"
    test_success = "✓ 连接成功"
    test_failure = lambda msg: f"✗ {msg}"  # type: ignore[assignment]
    test_running = "测试中..."
    plugins_manage = "管理插件"
    settings_saved = "设置已保存"
    settings_invalid_url = "URL 格式无效"

    # --- Plugins view (Phase 5) ---
    plugins_back = "返回"
    plugins_refresh = "刷新"
    plugins_empty = "(尚未安装任何插件)"
    plugins_install_hint = "安装新插件: pip install markitdown-xxx,然后点击刷新"
    plugins_version = "版本"
    plugins_source = "来源"
    plugins_enable = "启用"
    plugin_loaded_count = lambda n: f"已安装插件 ({n})"  # type: ignore[assignment]
    plugin_load_warning = "插件管理仅控制已加载的插件,无法禁用导入失败的插件"

    # --- About view (Phase 5) ---
    about_back = "返回"
    about_subtitle = "Powered by Flet & markitdown"
    about_core_version = "markitdown 核心版本"
    about_flet_version = "Flet 版本"
    about_python_version = "Python 版本"
    about_github = "GitHub: github.com/microsoft/markitdown"
    about_docs = "文档: 见 markitdown 主仓库 README"
    about_license = "MIT License"

    # --- Generic error/info ---
    error_unknown = "未知错误"
    error_network = "网络错误"
    error_unsupported_format = "不支持的格式"
    error_missing_dep = "缺少依赖"
    info_copied = "已复制到剪贴板"
    info_saved_to = lambda path: f"已保存到 {path}"  # type: ignore[assignment]
    warning_keyring_fallback = "系统钥匙串不可用,已降级到加密本地存储。请尽快备份配置。"
