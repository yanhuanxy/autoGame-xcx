"""
视觉流程自动化系统主界面 —— 精简 shell（Phase E2）。

仅承担：窗口外壳 + 左侧导航（NavSideBar）+ QStackedWidget 路由 + 状态栏 +
跨页编排（launch_advanced_creator）。各页内容已迁至 ``ui/pages/``：
项目介绍 / 模板管理 / 模板创建 / 操作说明 / MCP 服务。
"""
import os
import sys
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from autogame_xcx.ui import icons
from autogame_xcx.ui.controllers import AppController
from autogame_xcx.ui.pages import CreatorPage, GuidePage, IntroPage, ManagementPage
from autogame_xcx.ui.theme import MONO_FAMILIES, C
from autogame_xcx.ui.widgets import ConsoleStatusBar, NavButton
from autogame_xcx.utils.constants import TEMPLATES_PATH


class MainGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = AppController()
        # core 单件经 AppController 持有；此处别名保留既有属性引用（MCP 桥 / launch）
        self.window_controller = self.controller.window_controller
        self.image_matcher = self.controller.image_matcher
        self.template_manager = self.controller.template_manager
        self.game_executor = self.controller.game_executor
        self.report_generator = self.controller.report_generator

        # MCP 服务（替代旧 RemoteDriver）：在独立 QThread 跑 SSE server，
        # 让 wechat-ilink-bot 通过 MCP 协议发现并调用本项目能力。
        self.mcp_server = self._build_mcp_server()

        # 当前状态
        self.current_template = None
        self.current_screenshot = None
        self.marked_areas = []

        self.init_ui()

    def init_ui(self):
        self.setObjectName("MainGUI")
        self.setWindowTitle("视觉流程自动化系统 - 智能模板管理平台")
        self.setGeometry(100, 100, 1300, 800)
        self.setMinimumSize(1000, 800)
        # 主题在 QApplication 层应用（start_main_gui.py 调 apply_theme）

        # 创建中央部件
        central_widget = QWidget()
        central_widget.setObjectName("MainCentral")
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航栏（设计稿 200px 深色）
        self.menu_panel = self.create_menu_panel()
        main_layout.addWidget(self.menu_panel)

        # 右侧内容区
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentStack")
        main_layout.addWidget(self.content_stack)

        # 各页面
        self.create_pages()

        # 状态栏
        self.create_status_bar()

        # 默认显示项目介绍
        self.show_project_intro()

    def create_menu_panel(self):
        """创建左侧导航栏（设计稿：200px 深色，logo + 5 NavButton + 版本信息）"""
        mono = MONO_FAMILIES[0]
        menu_widget = QWidget()
        menu_widget.setObjectName("NavSideBar")
        menu_widget.setFixedWidth(200)
        layout = QVBoxLayout(menu_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # logo 区
        logo = QWidget()
        logo.setStyleSheet(f"border-bottom: 1px solid {C.BORDER};")
        logo_layout = QHBoxLayout(logo)
        logo_layout.setContentsMargins(16, 14, 16, 14)
        logo_layout.setSpacing(10)
        logo_icon = QLabel()
        logo_icon.setFixedSize(32, 32)
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setStyleSheet(f"background-color: {C.ACCENT}; border-radius: 8px;")
        logo_icon.setPixmap(icons.pixmap("logo", "#ffffff", 18))
        title = QLabel("视觉流程自动化")
        title.setStyleSheet(f"color: {C.TEXT}; font-size: 13px; font-weight: 600;")
        sub = QLabel("v2.0 · AUTO")
        sub.setStyleSheet(f"color: {C.TEXT_4}; font-family: '{mono}'; font-size: 10px; letter-spacing: 0.5px;")
        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(2)
        text_box.addWidget(title)
        text_box.addWidget(sub)
        logo_layout.addWidget(logo_icon)
        logo_layout.addLayout(text_box)
        logo_layout.addStretch()
        layout.addWidget(logo)

        # 导航项
        self.menu_group = QButtonGroup(self)
        self.menu_group.setExclusive(True)
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(2)
        menu_items = [
            ("项目介绍", "nav.intro", self.show_project_intro),
            ("模板管理", "nav.management", self.show_template_management),
            ("模板创建", "nav.creator", self.show_template_creator),
            ("操作说明", "nav.guide", self.show_user_guide),
            ("MCP 服务", "nav.mcp", self.show_mcp_server),
        ]
        for text, icon_name, callback in menu_items:
            btn = NavButton(text, icon_name)
            btn.clicked.connect(callback)
            self.menu_group.addButton(btn)
            nav_layout.addWidget(btn)
        nav_layout.addStretch()
        layout.addWidget(nav_container)

        # 底部版本信息
        info_widget = QWidget()
        info_widget.setStyleSheet(f"border-top: 1px solid {C.BORDER};")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(0)
        for text in ("VERSION  Phase 2.0", f"UPDATED  {datetime.now().strftime('%Y-%m-%d')}"):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {C.TEXT_4}; font-family: '{mono}'; font-size: 10px;")
            info_layout.addWidget(lbl)
        layout.addWidget(info_widget)

        return menu_widget

    def create_pages(self):
        """创建各个页面（顺序 = content_stack 索引 0-4，导航契约锁定）"""
        # 0 项目介绍
        self.intro_page = IntroPage()
        self.content_stack.addWidget(self.intro_page)

        # 1 模板管理
        self.management_page = self.create_management_page()
        self.content_stack.addWidget(self.management_page)

        # 2 模板创建
        self.creator_page = self.create_creator_page()
        self.content_stack.addWidget(self.creator_page)

        # 3 操作说明
        self.guide_page = GuidePage()
        self.content_stack.addWidget(self.guide_page)

        # 4 MCP 服务
        self.remote_page = self.create_remote_page()
        self.content_stack.addWidget(self.remote_page)

    def create_management_page(self):
        """模板管理页面（UI+逻辑已迁至 ui/pages/management_page.py）"""
        return ManagementPage(self)

    def create_creator_page(self):
        """创建模板创建页面（IntegratedTemplateCreator 已迁至 ui/pages/creator_page.py）"""
        page = CreatorPage(self)
        # 保留 integrated_creator 引用：launch_advanced_creator 加载模板时用到
        self.integrated_creator = page.creator
        return page

    def create_status_bar(self):
        """创建状态栏（设计稿：26px，mono，左 status dot+页名，右 上下文+Phase）"""
        self._console_status = ConsoleStatusBar()
        self.setStatusBar(self._console_status)

    # 菜单切换方法
    def show_project_intro(self):
        """显示项目介绍"""
        self.content_stack.setCurrentIndex(0)
        self._console_status.set_page("项目介绍")

    def show_template_management(self):
        """显示模板管理"""
        self.content_stack.setCurrentIndex(1)
        self.management_page.refresh_templates()
        self._console_status.set_page("模板管理")

    def show_template_creator(self):
        """显示模板创建"""
        self.content_stack.setCurrentIndex(2)
        self._console_status.set_page("模板创建")

    def show_user_guide(self):
        """显示操作说明"""
        self.content_stack.setCurrentIndex(3)
        self._console_status.set_page("操作说明")

    def show_mcp_server(self):
        """显示 MCP 服务页面"""
        self.content_stack.setCurrentIndex(4)
        self._console_status.set_page("MCP 服务")

    def create_remote_page(self):
        """构造 MCP 服务页面（McpServerPage 包装 mcp_server thread）"""
        from autogame_xcx.ui.dialogs.mcp_server_page import McpServerPage

        return McpServerPage(self.mcp_server, parent=self)

    def _build_mcp_server(self):
        """构造 McpServerThread。注入 executor + template_manager。

        host/鉴权 token 从 data/mcp_server_config.json 加载（迭代C，缺省 127.0.0.1 + 不鉴权，向后兼容）。
        线程不会立刻 start；用户在 UI 上点"启动"后才 start。
        """
        from autogame_xcx.mcp import ExecutorBridge, McpServerThread, load_server_config

        server_config = load_server_config()
        bridge = ExecutorBridge(
            executor=self.game_executor,
            template_manager=self.template_manager,
            queue_capacity=server_config.queue_capacity,
            queue_wait_timeout_seconds=server_config.queue_wait_timeout_seconds,
            execution_timeout_seconds=server_config.execution_timeout_seconds,
        )
        return McpServerThread(
            bridge=bridge,
            port=8765,
            host=server_config.host,
            auth_token=server_config.auth_token,
        )

    def refresh_templates(self) -> None:
        """代理：刷新模板管理页列表（供模板创建页保存后调用）。"""
        self.management_page.refresh_templates()

    def launch_advanced_creator(self, template_file=None):
        """切换到集成的创建工具"""
        # 切换到模板创建页面
        self.show_template_creator()

        # 如果指定了模板文件，加载它
        if template_file:
            try:
                template_path = os.path.join(TEMPLATES_PATH, template_file)
                if os.path.exists(template_path):
                    template = self.template_manager.load_template(template_path)
                    if template and hasattr(self, 'integrated_creator'):
                        self.integrated_creator.load_template_data(template)
                        self.current_template = template
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载模板失败: {str(e)}")


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("视觉流程自动化系统")
    app.setApplicationVersion("Phase 2.0")
    app.setOrganizationName("AutoGame Team")

    # 创建主窗口
    window = MainGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
