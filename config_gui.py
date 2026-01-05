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
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("文件监控配置管理")
        self.root.geometry("800x500")
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
            config = {
                "mappings": self.mappings,
                "settings": self.config_manager.get_settings()
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
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
        
        # 列表框架
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 列表标题
        list_header = ttk.Label(list_frame, text="当前配置的映射关系：", font=("Arial", 10))
        list_header.pack(anchor=tk.W)
        
        # 创建树形视图（列表）
        columns = ("序号", "源文件", "目标目录", "自动打开")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        
        # 设置列
        self.tree.heading("序号", text="序号")
        self.tree.heading("源文件", text="源文件")
        self.tree.heading("目标目录", text="目标目录")
        self.tree.heading("自动打开", text="自动打开")
        
        self.tree.column("序号", width=50, anchor=tk.CENTER)
        self.tree.column("源文件", width=300)
        self.tree.column("目标目录", width=300)
        self.tree.column("自动打开", width=80, anchor=tk.CENTER)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="添加映射", command=self.add_mapping).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="编辑选中", command=self.edit_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="删除选中", command=self.delete_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="刷新列表", command=self.refresh_list).pack(side=tk.LEFT, padx=(0, 5))
        
        # 底部按钮框架
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)
        
        ttk.Button(bottom_frame, text="保存配置", command=self.save_config).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(bottom_frame, text="取消", command=self.root.destroy).pack(side=tk.RIGHT)
    
    def refresh_list(self):
        """刷新列表显示"""
        # 清空列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加映射项
        for i, mapping in enumerate(self.mappings, 1):
            source_file = mapping.get('source_file', '')
            target_dir = mapping.get('target_dir', '')
            open_dir = "是" if mapping.get('open_dir', False) else "否"
            
            # 截断过长的路径显示
            if len(source_file) > 50:
                source_file_display = "..." + source_file[-47:]
            else:
                source_file_display = source_file
            
            if len(target_dir) > 50:
                target_dir_display = "..." + target_dir[-47:]
            else:
                target_dir_display = target_dir
            
            self.tree.insert("", tk.END, values=(i, source_file_display, target_dir_display, open_dir), tags=(i-1,))
    
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
        self.dialog.geometry("600x250")
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
        
        # 自动打开目录
        self.open_dir_var = tk.BooleanVar(value=mapping.get('open_dir', False) if mapping else False)
        ttk.Checkbutton(main_frame, text="复制后自动打开目标目录", variable=self.open_dir_var).grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
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
        
        self.result = {
            "source_file": source_file,
            "target_dir": target_dir,
            "open_dir": self.open_dir_var.get()
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

