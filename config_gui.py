"""
配置文件图形界面
提供友好的GUI界面来管理文件-目录映射配置
"""
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import List, Dict, Optional
from config_manager import ConfigManager


class ConfigGUI:
    """配置管理GUI界面"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化配置GUI
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config_manager = ConfigManager(str(self.config_path))
        self.mappings: List[Dict] = []
        self.project_vars: Dict[str, tk.BooleanVar] = {}  # 项目选择变量
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("文件监控配置管理")
        self.root.geometry("900x600")
        self.root.resizable(True, True)
        
        # 加载配置
        self.load_config()
        
        # 创建界面
        self.create_widgets()
        
        # 刷新列表
        self.refresh_list()
    
    def load_config(self):
        """加载配置"""
        if self.config_path.exists():
            self.config_manager.load_config()
            self.mappings = self.config_manager.get_mappings().copy()
        else:
            self.mappings = []
    
    def save_config(self):
        """保存配置"""
        try:
            # 更新项目启用状态
            projects = self.config_manager.get_projects()
            for project_name, var in self.project_vars.items():
                if project_name in projects:
                    self.config_manager.set_project_enabled(project_name, var.get())
            
            # 保存配置（包括项目状态）
            if not self.config_manager.save_config():
                messagebox.showerror("错误", "保存配置失败")
                return False
            
            # 创建刷新信号文件，通知运行中的程序刷新配置
            signal_file = Path(self.config_path.parent / ".reload_config")
            try:
                signal_file.touch()
            except:
                pass  # 如果创建信号文件失败，不影响保存
            
            messagebox.showinfo("成功", "配置已保存！\n\n程序将自动刷新配置。")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败：{e}")
            return False
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="文件监控配置管理", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 创建左右分栏
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 左侧：项目选择区域
        left_frame = ttk.Frame(paned, width=250)
        paned.add(left_frame, weight=1)
        self.create_project_selection(left_frame)
        
        # 右侧：映射列表区域
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        self.create_mapping_list(right_frame)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 底部按钮框架
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)
        
        ttk.Button(bottom_frame, text="保存配置", command=self.save_config).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(bottom_frame, text="取消", command=self.root.destroy).pack(side=tk.RIGHT)
    
    def create_project_selection(self, parent):
        """创建项目选择区域"""
        # 项目选择标题
        project_label = ttk.Label(parent, text="项目选择：", font=("Arial", 10, "bold"))
        project_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 全选/全不选按钮
        select_frame = ttk.Frame(parent)
        select_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(select_frame, text="全选", command=self.select_all_projects).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(select_frame, text="全不选", command=self.deselect_all_projects).pack(side=tk.LEFT)
        
        # 项目列表框架（带滚动条）
        project_list_frame = ttk.Frame(parent)
        project_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Canvas和Scrollbar用于项目列表
        canvas = tk.Canvas(project_list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(project_list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.project_content = ttk.Frame(canvas)
        
        self.project_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.project_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 刷新项目列表
        self.refresh_project_list()
    
    def create_mapping_list(self, parent):
        """创建映射列表区域"""
        # 列表标题
        list_header = ttk.Label(parent, text="当前配置的映射关系：", font=("Arial", 10))
        list_header.pack(anchor=tk.W, pady=(0, 5))
        
        # 创建树形视图（列表）
        columns = ("序号", "源文件", "目标目录")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        
        # 设置列
        self.tree.heading("序号", text="序号")
        self.tree.heading("源文件", text="源文件")
        self.tree.heading("目标目录", text="目标目录")
        
        self.tree.column("序号", width=50, anchor=tk.CENTER)
        self.tree.column("源文件", width=300)
        self.tree.column("目标目录", width=300)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="添加映射", command=self.add_mapping).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="编辑选中", command=self.edit_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="删除选中", command=self.delete_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="刷新列表", command=self.refresh_list).pack(side=tk.LEFT, padx=(0, 5))
    
    def refresh_project_list(self):
        """刷新项目列表"""
        # 清空现有项目
        for widget in self.project_content.winfo_children():
            widget.destroy()
        self.project_vars.clear()
        
        # 获取项目信息
        projects = self.config_manager.get_projects()
        
        if not projects:
            ttk.Label(self.project_content, text="未识别到项目", foreground="gray").pack(anchor=tk.W, pady=5)
            return
        
        # 为每个项目创建复选框
        for project_name, project_info in sorted(projects.items()):
            frame = ttk.Frame(self.project_content)
            frame.pack(fill=tk.X, pady=2)
            
            # 创建复选框
            var = tk.BooleanVar(value=project_info.get('enabled', True))
            self.project_vars[project_name] = var
            
            checkbox = ttk.Checkbutton(
                frame,
                text=project_name,
                variable=var,
                command=lambda pn=project_name: self.on_project_toggle(pn)
            )
            checkbox.pack(side=tk.LEFT, anchor=tk.W)
            
            # 显示映射数量
            count = len(project_info.get('mapping_indices', []))
            count_label = ttk.Label(frame, text=f"({count}个映射)", foreground="gray", font=("Arial", 8))
            count_label.pack(side=tk.LEFT, padx=(5, 0))
    
    def on_project_toggle(self, project_name: str):
        """项目选择切换时的回调"""
        # 刷新映射列表，只显示选中项目的映射
        self.refresh_list()
    
    def select_all_projects(self):
        """全选所有项目"""
        for var in self.project_vars.values():
            var.set(True)
        self.refresh_list()
    
    def deselect_all_projects(self):
        """全不选所有项目"""
        for var in self.project_vars.values():
            var.set(False)
        self.refresh_list()
    
    def refresh_list(self):
        """刷新列表显示（只显示选中项目的映射）"""
        # 清空列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 获取启用的项目
        enabled_projects = set()
        for project_name, var in self.project_vars.items():
            if var.get():
                projects = self.config_manager.get_projects()
                if project_name in projects:
                    enabled_projects.update(projects[project_name].get('mapping_indices', []))
        
        # 只显示启用项目的映射
        display_index = 1
        for i, mapping in enumerate(self.mappings):
            if i in enabled_projects:
                source_file = mapping.get('source_file', '')
                target_dir = mapping.get('target_dir', '')
                
                # 截断过长的路径显示
                if len(source_file) > 60:
                    source_file_display = "..." + source_file[-57:]
                else:
                    source_file_display = source_file
                
                if len(target_dir) > 60:
                    target_dir_display = "..." + target_dir[-57:]
                else:
                    target_dir_display = target_dir
                
                self.tree.insert("", tk.END, values=(display_index, source_file_display, target_dir_display), tags=(i,))
                display_index += 1
    
    def add_mapping(self):
        """添加新的映射"""
        dialog = MappingDialog(self.root, "添加映射")
        if dialog.result:
            self.mappings.append(dialog.result)
            self.refresh_list()
    
    def edit_selected(self):
        """编辑选中的映射"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一个映射项")
            return
        
        # 获取选中项的索引
        item = self.tree.item(selected[0])
        tags = item['tags']
        if not tags:
            return
        
        index = int(tags[0])
        if index < 0 or index >= len(self.mappings):
            return
        
        # 打开编辑对话框
        dialog = MappingDialog(self.root, "编辑映射", self.mappings[index])
        if dialog.result:
            self.mappings[index] = dialog.result
            self.refresh_list()
    
    def delete_selected(self):
        """删除选中的映射"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一个映射项")
            return
        
        # 确认删除
        if not messagebox.askyesno("确认", "确定要删除选中的映射吗？"):
            return
        
        # 获取选中项的索引
        item = self.tree.item(selected[0])
        tags = item['tags']
        if not tags:
            return
        
        index = int(tags[0])
        if 0 <= index < len(self.mappings):
            del self.mappings[index]
            self.refresh_list()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()


class MappingDialog:
    """映射配置对话框"""
    
    def __init__(self, parent, title: str, mapping: Optional[Dict] = None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            title: 对话框标题
            mapping: 要编辑的映射（如果为None则创建新映射）
        """
        self.result = None
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x180")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # 创建组件
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 源文件
        ttk.Label(main_frame, text="源文件：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.source_file_var = tk.StringVar(value=mapping.get('source_file', '') if mapping else '')
        source_frame = ttk.Frame(main_frame)
        source_frame.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(10, 0))
        ttk.Entry(source_frame, textvariable=self.source_file_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(source_frame, text="选择文件", command=self.select_source_file).pack(side=tk.LEFT, padx=(5, 0))
        
        # 目标目录
        ttk.Label(main_frame, text="目标目录：").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.target_dir_var = tk.StringVar(value=mapping.get('target_dir', '') if mapping else '')
        target_frame = ttk.Frame(main_frame)
        target_frame.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(10, 0))
        ttk.Entry(target_frame, textvariable=self.target_dir_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(target_frame, text="选择目录", command=self.select_target_dir).pack(side=tk.LEFT, padx=(5, 0))
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="确定", command=self.ok_clicked).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)
        
        # 配置列权重
        main_frame.columnconfigure(1, weight=1)
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def select_source_file(self):
        """选择源文件"""
        filename = filedialog.askopenfilename(
            title="选择要监控的文件",
            filetypes=[("所有文件", "*.*")]
        )
        if filename:
            self.source_file_var.set(filename)
    
    def select_target_dir(self):
        """选择目标目录"""
        dirname = filedialog.askdirectory(title="选择目标目录")
        if dirname:
            self.target_dir_var.set(dirname)
    
    def ok_clicked(self):
        """确定按钮点击"""
        source_file = self.source_file_var.get().strip()
        target_dir = self.target_dir_var.get().strip()
        
        if not source_file:
            messagebox.showwarning("提示", "请选择源文件")
            return
        
        if not target_dir:
            messagebox.showwarning("提示", "请选择目标目录")
            return
        
        # 固定配置：始终打开目录，始终等待文件写入完成，使用默认时间参数
        self.result = {
            "source_file": source_file,
            "target_dir": target_dir,
            "open_dir": True,  # 始终打开目录
            "wait_for_complete": True,  # 始终等待文件写入完成
            "wait_timeout": 10.0,  # 默认10秒
            "check_interval": 0.2,  # 默认0.2秒
            "initial_delay": 0.5  # 默认0.5秒
        }
        
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """取消按钮点击"""
        self.dialog.destroy()


def open_config_gui(config_path: str = "config.json"):
    """
    打开配置GUI界面
    
    Args:
        config_path: 配置文件路径
    """
    app = ConfigGUI(config_path)
    app.run()


if __name__ == "__main__":
    open_config_gui()

