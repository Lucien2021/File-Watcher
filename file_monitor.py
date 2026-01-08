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
    
    def __init__(self, source_file: str, target_dir: str, open_dir: bool = False, 
                 wait_for_complete: bool = True, wait_timeout: float = 10.0, 
                 check_interval: float = 0.2, initial_delay: float = 0.5,
                 logger: Optional[logging.Logger] = None):
        """
        初始化文件同步处理器
        
        Args:
            source_file: 源文件完整路径
            target_dir: 目标目录
            open_dir: 是否在复制后打开目录
            wait_for_complete: 是否等待文件写入完成（默认True）
            wait_timeout: 最大等待时间（秒，默认10秒）
            check_interval: 文件稳定性检查间隔（秒，默认0.2秒）
            initial_delay: 初始延迟时间（秒，默认0.5秒）
            logger: 日志记录器
        """
        self.source_file = Path(source_file)
        self.target_dir = Path(target_dir)
        self.open_dir = open_dir
        self.wait_for_complete = wait_for_complete
        self.wait_timeout = wait_timeout
        self.check_interval = check_interval
        self.initial_delay = initial_delay
        self.logger = logger or logging.getLogger(__name__)
        self.last_copy_time = {}  # 记录每个文件的最后复制时间，避免重复复制
        self.stable_check_count = 3  # 需要连续稳定的次数
        
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
            
            # 等待文件写入完成（如果启用）
            if self.wait_for_complete:
                if not self._wait_for_file_ready(event_file):
                    self.logger.warning(f"文件未能在超时时间内就绪，跳过复制: {event_file}")
                    return
            
            # 执行复制操作
            self._copy_file(event_file)
            
        except Exception as e:
            self.logger.error(f"处理文件事件失败: {e}")
    
    def _wait_for_file_ready(self, file_path: Path) -> bool:
        """
        等待文件写入完成
        
        通过检测文件大小稳定性和文件锁定状态来判断文件是否写入完成
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否就绪（True表示就绪，False表示超时）
        """
        try:
            # 初始延迟，给写入过程留出时间
            if self.initial_delay > 0:
                time.sleep(self.initial_delay)
            
            start_time = time.time()
            last_size = -1
            stable_count = 0
            
            while time.time() - start_time < self.wait_timeout:
                try:
                    # 检查文件是否存在
                    if not file_path.exists():
                        time.sleep(self.check_interval)
                        continue
                    
                    # 获取文件大小
                    current_size = file_path.stat().st_size
                    
                    # 检查文件大小是否稳定
                    if current_size == last_size:
                        stable_count += 1
                        # 如果文件大小连续稳定N次，认为写入完成
                        if stable_count >= self.stable_check_count:
                            # 再次检查文件是否被锁定
                            if self._is_file_unlocked(file_path):
                                elapsed = time.time() - start_time
                                self.logger.debug(f"文件写入完成，等待时间: {elapsed:.2f}秒, 文件大小: {current_size} 字节")
                                return True
                    else:
                        # 文件大小变化，重置稳定计数
                        stable_count = 0
                        last_size = current_size
                        self.logger.debug(f"文件大小变化: {current_size} 字节")
                    
                    # 等待一段时间后再次检查
                    time.sleep(self.check_interval)
                    
                except OSError as e:
                    # 文件可能被锁定或正在写入
                    stable_count = 0
                    time.sleep(self.check_interval)
                    continue
            
            # 超时
            elapsed = time.time() - start_time
            self.logger.warning(f"等待文件就绪超时: {file_path}, 等待时间: {elapsed:.2f}秒")
            return False
            
        except Exception as e:
            self.logger.error(f"等待文件就绪时出错: {e}")
            return False
    
    def _is_file_unlocked(self, file_path: Path) -> bool:
        """
        检查文件是否未被锁定（可以打开）
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否未被锁定
        """
        try:
            # 尝试以独占模式打开文件
            # 如果能打开，说明文件已释放（写入完成）
            with open(file_path, 'r+b') as f:
                # 尝试读取文件末尾，确保文件可读
                f.seek(0, 2)  # 移动到文件末尾
                return True
        except (PermissionError, IOError, OSError):
            # 文件被锁定，仍在写入中
            return False
        except Exception:
            # 其他错误，保守处理，认为文件未就绪
            return False
    
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
            
            # 获取文件等待相关配置
            wait_for_complete = mapping.get('wait_for_complete', True)  # 默认启用
            wait_timeout = mapping.get('wait_timeout', 10.0)  # 默认10秒
            check_interval = mapping.get('check_interval', 0.2)  # 默认0.2秒
            initial_delay = mapping.get('initial_delay', 0.5)  # 默认0.5秒
            
            # 创建事件处理器
            handler = FileSyncHandler(
                source_file=str(source_file),
                target_dir=str(target_dir),
                open_dir=open_dir,
                wait_for_complete=wait_for_complete,
                wait_timeout=wait_timeout,
                check_interval=check_interval,
                initial_delay=initial_delay,
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

