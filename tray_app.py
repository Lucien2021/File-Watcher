"""
系统托盘应用
提供系统托盘图标和菜单功能
"""
import os
import sys
import logging
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
            pystray.MenuItem("查看日志", self._open_log),
            pystray.MenuItem("编辑配置", self._edit_config),
            pystray.MenuItem("刷新配置", self._reload_config),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("关于", self._show_about),
            pystray.MenuItem("退出", self._quit_app)
        ]
        
        return pystray.Menu(*menu_items)
    
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
    
    def _reload_config(self, icon, item):
        """重新加载配置"""
        try:
            self.logger.info("重新加载配置...")
            
            # 停止当前监控
            if self.file_monitor:
                self.file_monitor.stop()
            
            # 重新加载配置
            if self.config_manager.load_config():
                # 重新创建并启动监控
                from file_monitor import FileMonitor
                self.file_monitor = FileMonitor(
                    self.config_manager.get_mappings(),
                    self.logger
                )
                self.file_monitor.start()
                self.logger.info("配置已重新加载")
            else:
                self.logger.error("重新加载配置失败")
        except Exception as e:
            self.logger.error(f"重新加载配置失败: {e}")
    
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
            
            # 运行托盘图标（阻塞）
            self.icon.run()
            
        except Exception as e:
            self.logger.error(f"系统托盘应用运行失败: {e}")
            raise
    
    def stop(self):
        """停止系统托盘应用"""
        if self.icon:
            self.icon.stop()
        self.running = False

