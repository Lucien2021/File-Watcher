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
            
            # 验证配置
            if not self.validate_config():
                return False
                
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
            
            # 设置默认值
            if 'open_dir' not in mapping:
                mapping['open_dir'] = False
                
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

