# -*- coding: utf-8 -*-
"""
Internationalization support for Beer
"""

TRANSLATIONS = {
    'en': {
        # Navigation
        'main_page': 'Main',
        'log_page': 'Log',
        
        # Main window
        'app_title': 'Beer - Be Emulator morE Ruined',
        'proton_version': 'Proton Version',
        'proton_desc': 'Select the Proton version to use for running Windows programs',
        'custom_proton_enabled': 'Custom Proton path is enabled. Please disable it in Settings to use this option.',
        'program_path': 'Program Path',
        'program_desc': 'Path to the Windows executable (.exe) file',
        'run_directory': 'Run Directory',
        'run_dir_desc': 'Working directory when running the program (usually the program\'s folder)',
        'architecture': 'Architecture',
        'arch_desc': 'Select the architecture of the executable',
        'arch_32': '32-bit',
        'arch_64': '64-bit',
        'arch_auto': 'Auto-detect',
        'arch_32_desc': 'Use for older 32-bit applications',
        'arch_64_desc': 'Use for modern 64-bit applications',
        'arch_auto_desc': 'Automatically detect from executable',
        'more_options': 'More Options',
        'save_config': 'Save Config',
        'run': 'Run',
        'generate_desktop': 'Generate Desktop File',
        'program_name': 'Program Name',
        'program_name_desc': 'Display name for the desktop shortcut',
        
        # Buttons
        'browse': 'Browse',
        'select': 'Select',
        'save': 'Save',
        'cancel': 'Cancel',
        'reset': 'Reset to Default',
        'close': 'Close',
        'apply': 'Apply',
        'ok': 'OK',
        'yes': 'Yes',
        'no': 'No',
        'delete': 'Delete',
        'edit': 'Edit',
        'export': 'Export',
        'import': 'Import',
        'search': 'Search',
        
        # Settings
        'settings': 'Settings',
        'general_settings': 'General Settings',
        'advanced_settings': 'Advanced Settings',
        'custom_proton_path': 'Custom Proton Path',
        'custom_proton_desc': 'Enable to use a custom Proton installation path',
        'tool_directory': 'Tool Directory',
        'tool_dir_desc': 'Directory containing icon extraction tools (wrest/extract-icon). Required for generating desktop files with icons.',
        'tool_not_installed': 'Tools not installed. Cannot generate desktop files with icons.',
        'tool_available': 'Available tool',
        'install_tool': 'Install Tool',
        'proton_search_paths': 'Proton Search Paths',
        'proton_paths_desc': 'Directories to search for Proton installations',
        'default_page': 'Default Page',
        'default_page_desc': 'Page to show when starting the application',
        'theme': 'Theme',
        'theme_desc': 'Application theme',
        'theme_system': 'Follow System',
        'theme_light': 'Light',
        'theme_dark': 'Dark',
        'language': 'Language',
        'language_desc': 'Application language',
        'language_system': 'Follow System',
        
        # Advanced settings
        'environment_variables': 'Environment Variables',
        'env_vars_desc': 'Custom environment variables for Proton',
        'add': 'Add',
        'remove': 'Remove',
        'variable': 'Variable',
        'value': 'Value',
        
        # More options
        'startup_options': 'Startup Options',
        'startup_args': 'Startup Arguments',
        'startup_args_desc': 'Command line arguments to pass to the program',
        'batch_launch': 'Batch Launch',
        'batch_launch_desc': 'Launch multiple programs in sequence',
        'launch_interval': 'Launch Interval (seconds)',
        'launch_interval_desc': 'Time to wait between launching each program',
        'drag_to_reorder': 'Drag to reorder launch sequence',
        'command_script': 'Command Script',
        'command_script_desc': 'Script to run before launching the program',
        'pre_launch_script': 'Pre-launch Script',
        'pre_launch_desc': 'Shell script to execute before running the program',
        
        # Log panel
        'log': 'Log',
        'clear_log': 'Clear Log',
        'save_log': 'Save Log',
        'show_log_on_start': 'Show Log on Start',
        'show_log_desc': 'Automatically show log panel when starting an application',
        
        # Saved apps
        'saved_apps': 'Saved Applications',
        'saved_apps_desc': 'Double-click icon to launch, right-click for options, double-click name/description/Proton layer to edit',
        'no_saved_apps': 'No saved applications yet',
        'double_click_launch': 'Double-click icon to launch',
        'not_set': 'Not set',
        'confirm_delete': 'Confirm Delete',
        'confirm_delete_msg': 'Are you sure you want to delete this configuration?',
        'confirm_reset_msg': 'Are you sure you want to reset all settings to default?',
        'add_shortcut': 'Add Desktop Shortcut',
        'edit_name': 'Edit Name',
        'edit_desc': 'Edit Description',
        'enter_new_text': 'Enter new text:',
        'name_exists': 'A configuration with this name already exists.',
        'duplicate_name': 'A saved configuration with this name already exists. Overwrite?',
        
        # Messages
        'error': 'Error',
        'warning': 'Warning',
        'info': 'Information',
        'success': 'Success',
        'file_not_found': 'File not found',
        'invalid_path': 'Invalid path',
        'proton_not_found': 'Proton not found at the specified path',
        'exe_not_found': 'Executable not found',
        'desktop_file_generated': 'Desktop file generated successfully',
        'config_saved': 'Configuration saved',
        'config_reset': 'Configuration reset to defaults',
        'settings_saved': 'Settings saved',
        
        # File dialogs
        'select_proton': 'Select Proton Directory',
        'select_exe': 'Select Executable',
        'select_directory': 'Select Directory',
        'select_script': 'Select Script',
        'exe_files': 'Executable Files',
        'all_files': 'All Files',
        
        # Running
        'running': 'Running',
        'launching': 'Launching application...',
        'launch_failed': 'Failed to launch application',
        'launch_success': 'Application launched successfully',
        'process_ended': 'Process ended with code',
    },
    
    'zh': {
        # Navigation
        'main_page': '主页',
        'log_page': '日志',
        
        # Main window
        'app_title': 'Beer - 运行 Windows 程序的 Proton 启动器',
        'proton_version': 'Proton 版本',
        'proton_desc': '选择用于运行 Windows 程序的 Proton 版本',
        'custom_proton_enabled': '自定义 Proton 路径已启用。请在设置中禁用此选项以使用此功能。',
        'program_path': '程序路径',
        'program_desc': 'Windows 可执行文件 (.exe) 的路径',
        'run_directory': '运行目录',
        'run_dir_desc': '运行程序时的工作目录（通常是程序所在的文件夹）',
        'architecture': '架构',
        'arch_desc': '选择可执行文件的架构',
        'arch_32': '32位',
        'arch_64': '64位',
        'arch_auto': '自动检测',
        'arch_32_desc': '用于较旧的 32 位应用程序',
        'arch_64_desc': '用于现代的 64 位应用程序',
        'arch_auto_desc': '从可执行文件自动检测',
        'more_options': '更多选项',
        'save_config': '保存配置',
        'run': '运行',
        'generate_desktop': '生成桌面文件',
        'program_name': '程序名称',
        'program_name_desc': '桌面快捷方式的显示名称',
        
        # Buttons
        'browse': '浏览',
        'select': '选择',
        'save': '保存',
        'cancel': '取消',
        'reset': '恢复默认',
        'close': '关闭',
        'apply': '应用',
        'ok': '确定',
        'yes': '是',
        'no': '否',
        'delete': '删除',
        'edit': '编辑',
        'export': '导出',
        'import': '导入',
        'search': '搜索',
        
        # Settings
        'settings': '设置',
        'general_settings': '常规设置',
        'advanced_settings': '高级设置',
        'custom_proton_path': '自定义 Proton 路径',
        'custom_proton_desc': '启用以使用自定义的 Proton 安装路径',
        'tool_directory': '工具目录',
        'tool_dir_desc': '包含图标提取工具的目录（wrest/extract-icon）。生成带图标的桌面文件需要此工具。',
        'tool_not_installed': '工具未安装。无法生成带图标的桌面文件。',
        'proton_search_paths': 'Proton 搜索路径',
        'proton_paths_desc': '搜索 Proton 安装版本的目录',
        'default_page': '默认页面',
        'default_page_desc': '启动应用程序时显示的页面',
        'theme': '主题',
        'theme_desc': '应用程序主题',
        'theme_system': '跟随系统',
        'theme_light': '浅色',
        'theme_dark': '深色',
        'language': '语言',
        'language_desc': '应用程序语言',
        'language_system': '跟随系统',
        
        # Advanced settings
        'environment_variables': '环境变量',
        'env_vars_desc': 'Proton 的自定义环境变量',
        'add': '添加',
        'remove': '移除',
        'variable': '变量',
        'value': '值',
        
        # More options
        'startup_options': '启动选项',
        'startup_args': '启动参数',
        'startup_args_desc': '传递给程序的命令行参数',
        'batch_launch': '批量启动',
        'batch_launch_desc': '按顺序启动多个程序',
        'launch_interval': '启动间隔（秒）',
        'launch_interval_desc': '每个程序启动之间的等待时间',
        'drag_to_reorder': '拖拽以重新排序启动顺序',
        'command_script': '命令脚本',
        'command_script_desc': '启动程序前运行的脚本',
        'pre_launch_script': '预启动脚本',
        'pre_launch_desc': '运行程序前执行的 Shell 脚本',
        
        # Log panel
        'log': '日志',
        'clear_log': '清除日志',
        'save_log': '保存日志',
        'show_log_on_start': '启动时显示日志',
        'show_log_desc': '启动应用程序时自动显示日志面板',
        
        # Saved apps
        'saved_apps': '已保存的应用',
        'saved_apps_desc': '双击图标打开应用，右键查看选项，双击名称、描述和 Proton 层以修改',
        'no_saved_apps': '暂无已保存的应用程序',
        'double_click_launch': '双击图标启动',
        'not_set': '未设置',
        'confirm_delete': '确认删除',
        'confirm_delete_msg': '确定要删除此配置吗？',
        'confirm_reset_msg': '确定要将所有设置恢复为默认值吗？',
        'add_shortcut': '添加桌面快捷方式',
        'edit_name': '修改名称',
        'edit_desc': '修改描述',
        'enter_new_text': '输入新文本：',
        'name_exists': '已存在同名配置。',
        'duplicate_name': '已存在同名配置，是否覆盖？',
        
        # Messages
        'error': '错误',
        'warning': '警告',
        'info': '信息',
        'success': '成功',
        'file_not_found': '文件未找到',
        'invalid_path': '无效的路径',
        'proton_not_found': '在指定路径未找到 Proton',
        'exe_not_found': '未找到可执行文件',
        'desktop_file_generated': '桌面文件生成成功',
        'config_saved': '配置已保存',
        'config_reset': '配置已恢复默认',
        'settings_saved': '设置已保存',
        
        # File dialogs
        'select_proton': '选择 Proton 目录',
        'select_exe': '选择可执行文件',
        'select_directory': '选择目录',
        'select_script': '选择脚本',
        'exe_files': '可执行文件',
        'all_files': '所有文件',
        
        # Running
        'running': '运行中',
        'launching': '正在启动应用程序...',
        'launch_failed': '启动应用程序失败',
        'launch_success': '应用程序启动成功',
        'process_ended': '进程结束，退出码',
    }
}


class Translator:
    """Translation manager"""
    
    def __init__(self, language='system'):
        self.language = language
        self.resolved_language = self._resolve_language(language)
    
    def _resolve_language(self, language):
        """Resolve 'system' to actual language code"""
        if language == 'system':
            import locale
            try:
                lang = locale.getdefaultlocale()[0]
                if lang and lang.startswith('zh'):
                    return 'zh'
            except Exception:
                pass
            return 'en'
        return language if language in TRANSLATIONS else 'en'
    
    def set_language(self, language):
        """Set the current language"""
        self.language = language
        self.resolved_language = self._resolve_language(language)
    
    def get(self, key, default=None):
        """Get a translation by key"""
        translations = TRANSLATIONS.get(self.resolved_language, TRANSLATIONS['en'])
        return translations.get(key, default or key)
    
    def __call__(self, key, default=None):
        """Shortcut for get()"""
        return self.get(key, default)
