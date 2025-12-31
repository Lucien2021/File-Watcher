"""
文件监控核心逻辑
使用 watchdog 监控文件变化并执行复制操作
"""
import os
import shutil
import time
import logging
from pathlib import Path
from typing import Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent


class FileSyncHandler(FileSystemEventHandler):
    """文件同步事件处理器"""
    
    def __init__(self, source_file: str, target_dir: str, open_dir: bool = False, logger: Optional[logging.Logger] = None):
        """
        初始化文件同步处理器
        
        Args:
            source_file: 源文件完整路径
            target_dir: 目标目录
            open_dir: 是否在复制后打开目录
            logger: 日志记录器
        """
        self.source_file = Path(source_file)
        self.target_dir = Path(target_dir)
        self.open_dir = open_dir
        self.logger = logger or logging.getLogger(__name__)
        self.last_copy_time = {}  # 记录每个文件的最后复制时间，避免重复复制
        
    def on_modified(self, event):
        """文件修改事件"""
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def _handle_file_event(self, file_path: str):
        """
        处理文件事件
        
        Args:
            file_path: 文件路径
        """
        try:
            event_file = Path(file_path)
            
            # 检查是否是我们要监控的文件（完整文件名匹配）
            if event_file.resolve() != self.source_file.resolve():
                return
            
            # 检查文件是否存在
            if not event_file.exists():
                return
            
            # 避免频繁复制：检查文件修改时间
            try:
                mtime = event_file.stat().st_mtime
                if file_path in self.last_copy_time:
                    # 如果文件在1秒内被复制过，跳过
                    if mtime - self.last_copy_time[file_path] < 1.0:
                        return
                self.last_copy_time[file_path] = mtime
            except OSError:
                # 文件可能被锁定，稍后重试
                return
            
            # 执行复制操作
            self._copy_file(event_file)
            
        except Exception as e:
            self.logger.error(f"处理文件事件失败: {e}")
    
    def _copy_file(self, source_file: Path):
        """
        复制文件到目标目录
        
        Args:
            source_file: 源文件路径
        """
        try:
            # 确保目标目录存在
            self.target_dir.mkdir(parents=True, exist_ok=True)
            
            # 目标文件路径
            target_file = self.target_dir / source_file.name
            
            # 尝试复制文件（可能需要重试，因为文件可能被锁定）
            max_retries = 5
            retry_delay = 0.5
            
            for attempt in range(max_retries):
                try:
                    # 如果目标文件存在，先删除
                    if target_file.exists():
                        target_file.unlink()
                    
                    # 复制文件
                    shutil.copy2(source_file, target_file)
                    
                    # 记录日志
                    self.logger.info(f"文件已复制: {source_file} -> {target_file}")
                    
                    # 如果需要，打开目标目录
                    if self.open_dir:
                        self._open_directory(self.target_dir)
                    
                    return
                    
                except PermissionError:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        raise
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        raise
                        
        except Exception as e:
            self.logger.error(f"复制文件失败: {source_file} -> {self.target_dir}, 错误: {e}")
    
    def _open_directory(self, directory: Path):
        """
        打开目录（Windows 资源管理器）
        
        Args:
            directory: 目录路径
        """
        try:
            os.startfile(str(directory))
        except Exception as e:
            self.logger.warning(f"打开目录失败: {directory}, 错误: {e}")


class FileMonitor:
    """文件监控器"""
    
    def __init__(self, mappings: list, logger: Optional[logging.Logger] = None):
        """
        初始化文件监控器
        
        Args:
            mappings: 文件-目录映射列表
            logger: 日志记录器
        """
        self.mappings = mappings
        self.logger = logger or logging.getLogger(__name__)
        self.observers: list = []
        self.handlers: list = []
        
    def start(self):
        """启动文件监控"""
        self.logger.info("启动文件监控...")
        
        for mapping in self.mappings:
            source_file = Path(mapping['source_file'])
            target_dir = Path(mapping['target_dir'])
            open_dir = mapping.get('open_dir', False)
            
            # 检查源文件目录是否存在
            if not source_file.parent.exists():
                self.logger.warning(f"源文件目录不存在，跳过监控: {source_file.parent}")
                continue
            
            # 创建事件处理器
            handler = FileSyncHandler(
                source_file=str(source_file),
                target_dir=str(target_dir),
                open_dir=open_dir,
                logger=self.logger
            )
            self.handlers.append(handler)
            
            # 创建观察者并监控源文件所在目录
            observer = Observer()
            observer.schedule(handler, str(source_file.parent), recursive=False)
            observer.start()
            self.observers.append(observer)
            
            self.logger.info(f"开始监控文件: {source_file}")
        
        self.logger.info(f"文件监控已启动，共监控 {len(self.observers)} 个文件")
    
    def stop(self):
        """停止文件监控"""
        self.logger.info("停止文件监控...")
        
        for observer in self.observers:
            observer.stop()
        
        for observer in self.observers:
            observer.join(timeout=2)
        
        self.observers.clear()
        self.handlers.clear()
        
        self.logger.info("文件监控已停止")
    
    def is_alive(self) -> bool:
        """
        检查监控是否运行中
        
        Returns:
            bool: 是否运行中
        """
        return any(obs.is_alive() for obs in self.observers)

