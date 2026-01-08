"""
配置文件管理器
负责读取、验证和管理配置文件
"""
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional


class ConfigManager:
    """配置文件管理器"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config: Optional[Dict] = None
        self.mappings: List[Dict] = []
        self.settings: Dict = {}
        self.projects: Dict = {}  # 项目分组信息
        
    def _fix_json_paths(self, content: str) -> str:
        """
        修复 JSON 内容中的 Windows 路径反斜杠问题
        将路径字符串值中的单反斜杠转换为双反斜杠
        
        Args:
            content: JSON 文件内容
            
        Returns:
            str: 修复后的 JSON 内容
        """
        # 匹配 "source_file": "路径" 或 "target_dir": "路径"
        # 使用非贪婪匹配，确保只匹配到下一个引号
        pattern = r'("(?:source_file|target_dir)"\s*:\s*")([^"]+)(")'
        
        def replace_field(match):
            prefix = match.group(1)  # "source_file": " 或 "target_dir": "
            path = match.group(2)    # 路径内容
            suffix = match.group(3)   # 结束引号
            
            # 如果路径包含单反斜杠（且不是已转义的双反斜杠），则转义
            # 检查是否包含未转义的反斜杠
            if '\\' in path:
                # 先保护已转义的反斜杠（\\\\）
                temp_marker = '\x01\x01'
                path = path.replace('\\\\', temp_marker)
                # 替换剩余的单反斜杠为双反斜杠
                path = path.replace('\\', '\\\\')
                # 恢复已转义的反斜杠
                path = path.replace(temp_marker, '\\\\')
            
            return f'{prefix}{path}{suffix}'
        
        # 使用正则表达式替换路径字段
        fixed_content = re.sub(pattern, replace_field, content)
        
        return fixed_content
    
    def load_config(self) -> bool:
        """
        加载配置文件
        
        Returns:
            bool: 加载是否成功
        """
        try:
            if not self.config_path.exists():
                return False
            
            # 先读取文件内容
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试直接解析 JSON
            try:
                self.config = json.loads(content)
            except json.JSONDecodeError:
                # 如果解析失败，尝试修复路径中的反斜杠
                try:
                    fixed_content = self._fix_json_paths(content)
                    self.config = json.loads(fixed_content)
                except json.JSONDecodeError as e:
                    print(f"配置文件JSON格式错误: {e}")
                    print("提示: 请确保路径中的反斜杠已转义为双反斜杠（\\\\），或使用正斜杠（/）")
                    return False
                
            # 解析映射关系
            self.mappings = self.config.get('mappings', [])
            self.settings = self.config.get('settings', {})
            self.projects = self.config.get('projects', {})
            
            # 验证配置
            if not self.validate_config():
                return False
            
            # 识别项目并更新项目配置
            self._identify_projects()
                
            return True
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
    
    def validate_config(self) -> bool:
        """
        验证配置文件的有效性
        
        Returns:
            bool: 配置是否有效
        """
        if not isinstance(self.mappings, list):
            print("配置错误: mappings 必须是列表")
            return False
            
        for i, mapping in enumerate(self.mappings):
            if not isinstance(mapping, dict):
                print(f"配置错误: mappings[{i}] 必须是字典")
                return False
                
            # 检查必需字段
            required_fields = ['source_file', 'target_dir']
            for field in required_fields:
                if field not in mapping:
                    print(f"配置错误: mappings[{i}] 缺少必需字段 '{field}'")
                    return False
                    
            # 规范化路径
            source_file = Path(mapping['source_file']).resolve()
            target_dir = Path(mapping['target_dir']).resolve()
            
            # 检查源文件目录是否存在
            if not source_file.parent.exists():
                print(f"警告: 源文件目录不存在: {source_file.parent}")
                
            # 确保目标目录存在
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # 更新配置中的路径为绝对路径
            mapping['source_file'] = str(source_file)
            mapping['target_dir'] = str(target_dir)
            
            # 设置默认值（固定配置：始终打开目录，始终等待文件写入完成）
            mapping['open_dir'] = True  # 始终打开目录
            mapping['wait_for_complete'] = True  # 始终等待文件写入完成
            mapping['wait_timeout'] = 10.0  # 默认10秒超时
            mapping['check_interval'] = 0.2  # 默认0.2秒检查间隔
            mapping['initial_delay'] = 0.5  # 默认0.5秒初始延迟
                
        # 设置默认设置
        if 'log_file' not in self.settings:
            self.settings['log_file'] = 'sync_log.txt'
            
        return True
    
    def get_mappings(self) -> List[Dict]:
        """
        获取所有文件-目录映射
        
        Returns:
            List[Dict]: 映射列表
        """
        return self.mappings
    
    def get_settings(self) -> Dict:
        """
        获取设置
        
        Returns:
            Dict: 设置字典
        """
        return self.settings
    
    def get_config_path(self) -> Path:
        """
        获取配置文件路径
        
        Returns:
            Path: 配置文件路径
        """
        return self.config_path
    
    def _extract_project_name(self, source_path: Path, target_path: Path) -> str:
        """
        从路径中提取项目名称
        
        Args:
            source_path: 源文件路径
            target_path: 目标目录路径
            
        Returns:
            str: 项目名称
        """
        # 找到源文件和目标目录的最深共同父文件夹
        source_parts = source_path.parts
        target_parts = target_path.parts
        
        # 从根目录开始比较，找到共同部分
        common_parts = []
        min_len = min(len(source_parts), len(target_parts))
        for i in range(min_len):
            if source_parts[i] == target_parts[i]:
                common_parts.append(source_parts[i])
            else:
                break
        
        # 如果找到共同部分，使用最后一个作为项目标识
        # 通常项目名称在路径的较深层次
        if len(common_parts) > 0:
            # 尝试找到包含项目编号或名称的文件夹
            # 例如: "38 SCW非标（支持进出水压力传感器)"
            for part in reversed(common_parts):
                # 如果文件夹名包含数字开头或特定模式，可能是项目名
                if any(char.isdigit() for char in part) or len(part) > 10:
                    return part
            # 如果没有找到，使用最后一个共同部分
            return common_parts[-1]
        
        # 如果路径完全不同，尝试从源文件路径中提取
        # 查找包含数字开头的文件夹名
        for part in reversed(source_parts):
            if any(char.isdigit() for char in part) or len(part) > 10:
                return part
        
        # 如果都找不到，使用源文件路径的父目录名
        return source_path.parent.name if source_path.parent.name else "未知项目"
    
    def _identify_projects(self):
        """
        识别项目并分组映射
        """
        # 清空现有项目配置
        identified_projects = {}
        
        for i, mapping in enumerate(self.mappings):
            try:
                source_path = Path(mapping['source_file'])
                target_path = Path(mapping['target_dir'])
                
                # 提取项目名称
                project_name = self._extract_project_name(source_path, target_path)
                
                # 如果项目不存在，创建新项目
                if project_name not in identified_projects:
                    # 检查是否已有保存的配置
                    if project_name in self.projects:
                        enabled = self.projects[project_name].get('enabled', True)
                    else:
                        enabled = True  # 默认启用
                    
                    identified_projects[project_name] = {
                        'mapping_indices': [],
                        'enabled': enabled
                    }
                
                # 添加映射索引
                identified_projects[project_name]['mapping_indices'].append(i)
                
            except Exception as e:
                print(f"识别项目时出错 (映射 {i}): {e}")
                # 使用默认项目名
                default_name = "未分类项目"
                if default_name not in identified_projects:
                    identified_projects[default_name] = {
                        'mapping_indices': [],
                        'enabled': True
                    }
                identified_projects[default_name]['mapping_indices'].append(i)
        
        # 更新项目配置
        self.projects = identified_projects
    
    def get_projects(self) -> Dict:
        """
        获取所有项目信息
        
        Returns:
            Dict: 项目字典，格式为 {项目名: {enabled: bool, mapping_indices: List[int]}}
        """
        return self.projects
    
    def set_project_enabled(self, project_name: str, enabled: bool):
        """
        设置项目启用状态
        
        Args:
            project_name: 项目名称
            enabled: 是否启用
        """
        if project_name in self.projects:
            self.projects[project_name]['enabled'] = enabled
    
    def get_enabled_mappings(self) -> List[Dict]:
        """
        获取所有启用的项目的映射
        
        Returns:
            List[Dict]: 启用的映射列表
        """
        enabled_indices = set()
        for project_name, project_info in self.projects.items():
            if project_info.get('enabled', True):
                enabled_indices.update(project_info['mapping_indices'])
        
        # 返回启用的映射，保持原有顺序
        return [self.mappings[i] for i in sorted(enabled_indices) if i < len(self.mappings)]
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 保存是否成功
        """
        try:
            config = {
                'mappings': self.mappings,
                'projects': self.projects,
                'settings': self.settings
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

