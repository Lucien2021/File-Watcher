"""
系统托盘应用
提供系统托盘图标和菜单功能
"""
import os
import sys
import logging
import threading
import time
from pathlib import Path
from typing import Optional
import pystray
from PIL import Image, ImageDraw


class TrayApp:
    """系统托盘应用"""
    
    def __init__(self, config_manager, file_monitor, logger: Optional[logging.Logger] = None):
        """
        初始化系统托盘应用
        
        Args:
            config_manager: 配置管理器实例
            file_monitor: 文件监控器实例
            logger: 日志记录器
        """
        self.config_manager = config_manager
        self.file_monitor = file_monitor
        self.logger = logger or logging.getLogger(__name__)
        self.icon = None
        self.running = False
        self.reload_signal_file = self.config_manager.get_config_path().parent / ".reload_config"
        self.config_check_thread = None
        
    def _create_icon(self) -> Image.Image:
        """
        创建托盘图标
        
        Returns:
            Image.Image: 图标图像
        """
        # 创建一个简单的图标（16x16 像素）
        image = Image.new('RGB', (16, 16), color='white')
        draw = ImageDraw.Draw(image)
        
        # 绘制一个简单的文件夹图标
        # 外框
        draw.rectangle([2, 2, 14, 14], outline='blue', width=1)
        # 文件夹标签
        draw.polygon([(2, 2), (8, 2), (8, 4), (2, 4)], fill='blue')
        # 内部线条
        draw.line([(4, 6), (12, 6)], fill='blue', width=1)
        draw.line([(4, 9), (12, 9)], fill='blue', width=1)
        draw.line([(4, 12), (12, 12)], fill='blue', width=1)
        
        return image
    
    def _get_menu(self) -> pystray.Menu:
        """
        创建托盘菜单
        
        Returns:
            pystray.Menu: 菜单对象
        """
        menu_items = [
            pystray.MenuItem("配置管理", self._open_config_gui),
            pystray.MenuItem("查看日志", self._open_log),
            pystray.MenuItem("编辑配置", self._edit_config),
            pystray.MenuItem("刷新配置", self._reload_config),
            pystray.Menu.SEPARATOR,
        ]
        
        # 添加项目选择菜单
        project_menu_items = self._create_project_menu()
        if project_menu_items:
            menu_items.append(pystray.MenuItem("项目选择", pystray.Menu(*project_menu_items)))
            menu_items.append(pystray.Menu.SEPARATOR)
        
        menu_items.extend([
            pystray.MenuItem("关于", self._show_about),
            pystray.MenuItem("退出", self._quit_app)
        ])
        
        return pystray.Menu(*menu_items)
    
    def _create_project_menu(self) -> list:
        """创建项目选择菜单"""
        try:
            projects = self.config_manager.get_projects()
            if not projects:
                return []
            
            menu_items = []
            
            # 全选/全不选
            enabled_count = sum(1 for p in projects.values() if p.get('enabled', True))
            all_enabled = enabled_count == len(projects)
            
            menu_items.append(
                pystray.MenuItem(
                    "全选" if not all_enabled else "全不选",
                    self._toggle_all_projects
                )
            )
            menu_items.append(pystray.Menu.SEPARATOR)
            
            # 每个项目的菜单项
            for project_name, project_info in sorted(projects.items()):
                enabled = project_info.get('enabled', True)
                count = len(project_info.get('mapping_indices', []))
                menu_text = f"{'✓' if enabled else '○'} {project_name} ({count})"
                
                menu_items.append(
                    pystray.MenuItem(
                        menu_text,
                        lambda icon, item, pn=project_name: self._toggle_project(pn)
                    )
                )
            
            return menu_items
        except Exception as e:
            self.logger.error(f"创建项目菜单失败: {e}")
            return []
    
    def _toggle_project(self, project_name: str):
        """切换项目启用状态"""
        try:
            projects = self.config_manager.get_projects()
            if project_name not in projects:
                return
            
            # 切换状态
            current_state = projects[project_name].get('enabled', True)
            self.config_manager.set_project_enabled(project_name, not current_state)
            
            # 保存配置
            self.config_manager.save_config()
            
            # 重新加载配置以应用更改
            self._reload_config()
            
            self.logger.info(f"项目 '{project_name}' 已{'启用' if not current_state else '禁用'}")
        except Exception as e:
            self.logger.error(f"切换项目状态失败: {e}")
    
    def _toggle_all_projects(self, icon, item):
        """切换所有项目状态"""
        try:
            projects = self.config_manager.get_projects()
            if not projects:
                return
            
            # 检查当前状态
            enabled_count = sum(1 for p in projects.values() if p.get('enabled', True))
            all_enabled = enabled_count == len(projects)
            
            # 切换所有项目
            new_state = not all_enabled
            for project_name in projects.keys():
                self.config_manager.set_project_enabled(project_name, new_state)
            
            # 保存配置
            self.config_manager.save_config()
            
            # 重新加载配置
            self._reload_config()
            
            self.logger.info(f"所有项目已{'启用' if new_state else '禁用'}")
        except Exception as e:
            self.logger.error(f"切换所有项目状态失败: {e}")
    
    def _open_log(self, icon, item):
        """打开日志文件"""
        try:
            settings = self.config_manager.get_settings()
            log_file = settings.get('log_file', 'sync_log.txt')
            log_path = Path(log_file)
            
            if log_path.exists():
                os.startfile(str(log_path))
            else:
                # 如果日志文件不存在，尝试用记事本创建
                os.system(f'notepad "{log_path}"')
        except Exception as e:
            self.logger.error(f"打开日志文件失败: {e}")
    
    def _open_config_gui(self, icon, item):
        """打开配置管理GUI"""
        try:
            from config_gui import open_config_gui
            import threading
            
            # 在新线程中打开GUI，避免阻塞托盘
            def open_gui():
                try:
                    open_config_gui(str(self.config_manager.get_config_path()))
                except Exception as e:
                    self.logger.error(f"打开配置GUI失败: {e}")
            
            thread = threading.Thread(target=open_gui, daemon=True)
            thread.start()
        except Exception as e:
            self.logger.error(f"打开配置GUI失败: {e}")
    
    def _edit_config(self, icon, item):
        """编辑配置文件"""
        try:
            config_path = self.config_manager.get_config_path()
            if config_path.exists():
                os.startfile(str(config_path))
            else:
                # 如果配置文件不存在，尝试用记事本创建
                os.system(f'notepad "{config_path}"')
        except Exception as e:
            self.logger.error(f"打开配置文件失败: {e}")
    
    def _reload_config(self, icon=None, item=None):
        """重新加载配置"""
        try:
            self.logger.info("重新加载配置...")
            
            # 停止当前监控
            if self.file_monitor:
                self.file_monitor.stop()
            
            # 重新加载配置
            if self.config_manager.load_config():
                # 获取启用的映射
                enabled_mappings = self.config_manager.get_enabled_mappings()
                projects = self.config_manager.get_projects()
                enabled_projects = [name for name, info in projects.items() if info.get('enabled', True)]
                
                if not enabled_mappings:
                    self.logger.warning("没有启用的项目，停止监控")
                else:
                    # 重新创建并启动监控（只监控启用的映射）
                    from file_monitor import FileMonitor
                    self.file_monitor = FileMonitor(
                        enabled_mappings,
                        self.logger
                    )
                    self.file_monitor.start()
                    self.logger.info(f"配置已重新加载，监控 {len(enabled_projects)} 个项目，共 {len(enabled_mappings)} 个映射")
                
                # 删除刷新信号文件
                if self.reload_signal_file.exists():
                    try:
                        self.reload_signal_file.unlink()
                    except:
                        pass
            else:
                self.logger.error("重新加载配置失败")
        except Exception as e:
            self.logger.error(f"重新加载配置失败: {e}")
    
    def _check_config_reload(self):
        """检查是否需要重新加载配置（后台线程）"""
        while self.running:
            try:
                # 检查刷新信号文件
                if self.reload_signal_file.exists():
                    self.logger.info("检测到配置更新，自动刷新...")
                    self._reload_config()
            except Exception as e:
                self.logger.error(f"检查配置更新失败: {e}")
            
            # 每2秒检查一次
            time.sleep(2)
    
    def _show_about(self, icon, item):
        """显示关于信息"""
        import tkinter.messagebox as messagebox
        
        try:
            messagebox.showinfo(
                "关于",
                "文件监控自动同步工具\n\n"
                "版本: 1.0.0\n"
                "用于实时监控文件并自动复制到指定目录"
            )
        except Exception as e:
            self.logger.error(f"显示关于信息失败: {e}")
    
    def _quit_app(self, icon, item):
        """退出应用"""
        self.logger.info("退出应用...")
        self.running = False
        
        # 停止文件监控
        self.file_monitor.stop()
        
        # 停止托盘图标
        icon.stop()
    
    def run(self):
        """运行系统托盘应用"""
        try:
            # 创建图标
            icon_image = self._create_icon()
            
            # 创建菜单
            menu = self._get_menu()
            
            # 创建托盘图标
            self.icon = pystray.Icon("文件同步监控", icon_image, "文件监控自动同步工具", menu)
            
            self.running = True
            self.logger.info("系统托盘应用已启动")
            
            # 启动配置检查线程
            self.config_check_thread = threading.Thread(target=self._check_config_reload, daemon=True)
            self.config_check_thread.start()
            
            # 运行托盘图标（阻塞）
            self.icon.run()
            
        except Exception as e:
            self.logger.error(f"系统托盘应用运行失败: {e}")
            raise
    
    def stop(self):
        """停止系统托盘应用"""
        self.running = False
        if self.icon:
            self.icon.stop()
        # 等待配置检查线程结束
        if self.config_check_thread and self.config_check_thread.is_alive():
            self.config_check_thread.join(timeout=1)

