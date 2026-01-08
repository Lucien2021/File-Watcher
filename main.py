"""
文件监控自动同步工具 - 主程序入口
"""
import sys
import logging
from pathlib import Path
from config_manager import ConfigManager
from file_monitor import FileMonitor
from tray_app import TrayApp


def setup_logging(log_file: str = "sync_log.txt"):
    """
    设置日志记录
    
    Args:
        log_file: 日志文件路径
    """
    # 创建日志目录（如果不存在）
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 配置日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """主函数"""
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("文件监控自动同步工具启动")
    logger.info("=" * 50)
    
    try:
        # 初始化配置管理器
        config_manager = ConfigManager("config.json")
        
        # 加载配置
        if not config_manager.load_config():
            logger.error("加载配置文件失败，请检查 config.json 文件")
            logger.info("程序将退出")
            return 1
        
        # 获取配置
        all_mappings = config_manager.get_mappings()
        enabled_mappings = config_manager.get_enabled_mappings()
        settings = config_manager.get_settings()
        projects = config_manager.get_projects()
        
        if not all_mappings:
            logger.warning("配置文件中没有文件映射，请添加映射后重新启动")
            logger.info("程序将退出")
            return 1
        
        # 显示项目信息
        enabled_projects = [name for name, info in projects.items() if info.get('enabled', True)]
        logger.info(f"已加载 {len(all_mappings)} 个文件映射，共 {len(projects)} 个项目")
        logger.info(f"当前启用 {len(enabled_projects)} 个项目: {', '.join(enabled_projects)}")
        logger.info(f"将监控 {len(enabled_mappings)} 个映射")
        
        if not enabled_mappings:
            logger.warning("没有启用的项目，请至少启用一个项目")
            logger.info("程序将退出")
            return 1
        
        # 创建文件监控器（只监控启用的映射）
        file_monitor = FileMonitor(enabled_mappings, logger)
        
        # 启动文件监控
        file_monitor.start()
        
        # 创建系统托盘应用
        tray_app = TrayApp(config_manager, file_monitor, logger)
        
        # 运行系统托盘应用（阻塞）
        tray_app.run()
        
        logger.info("程序正常退出")
        return 0
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，程序退出")
        return 0
    except Exception as e:
        logger.exception(f"程序运行出错: {e}")
        return 1
    finally:
        # 确保清理资源
        try:
            if 'file_monitor' in locals():
                file_monitor.stop()
            if 'tray_app' in locals():
                tray_app.stop()
        except:
            pass


if __name__ == "__main__":
    sys.exit(main())

