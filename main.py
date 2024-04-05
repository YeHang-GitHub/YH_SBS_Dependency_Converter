import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, Listbox, Scrollbar, VERTICAL, Text, END, ttk, font
from ttkthemes import ThemedTk
# 增加 DPI 设置（适用于 Windows）
import ctypes

ctypes.windll.shcore.SetProcessDpiAwareness(1)
alias_change_step = 0

#这是接近最终版的一版，但是+按钮还存在bug

def scan_sbs_files(directory):
    """
    扫描给定目录下的所有.sbs文件，并返回一个包含所有文件路径的列表。
    """
    sbs_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.sbs'):
                sbs_files.append(os.path.join(root, file))
    return sbs_files

def extract_aliases(file_path):
    """
    从单个.sbs文件内容中提取aliases及其相关示例。
    """
    aliases_examples = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            matches = re.findall(r'(<filename v="([a-zA-Z0-9_]+)://[^"]+"/>)', content)
            for full_match, alias in matches:
                if alias not in aliases_examples:
                    aliases_examples[alias] = []
                aliases_examples[alias].append(full_match)
    except Exception as e:
        print(f"读取文件{file_path}时发生错误: {e}")
    return aliases_examples


def modify_sbs_file(file_path, alias_mapping):
    global alias_change_step
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        for old_alias, new_alias in alias_mapping.items():
            # 使用正则表达式来匹配并替换所有出现的old_alias
            pattern = re.compile(rf'({old_alias}://[^"/]+)')

            def replace_func(match):
                full_match = match.group(0)
                # 从完整匹配中去除old_alias及其后的'://'部分
                after_alias = full_match[len(old_alias) + 3:]  # +3 for '://'
                after_alias_step_applied = after_alias[max(0, alias_change_step):]
                # 根据步长调整进行替换
                return new_alias + after_alias_step_applied

            content = pattern.sub(replace_func, content)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

        return True, None

    except Exception as e:
        return False, str(e)





def create_gui():
    global global_font_bold, alias_change_step,selected_alias



    sbs_files = []  # 在函数顶层定义sbs_files
    aliases_examples = {}  # 存储aliases及其示例
    selected_alias = None  # 当前选中的alias

    def on_choose_directory():
        nonlocal sbs_files, aliases_examples
        directory = filedialog.askdirectory()
        if directory:
            directory_var.set(directory)
            update_aliases_list()

    def update_aliases_list():
        nonlocal sbs_files, aliases_examples
        directory = directory_var.get()
        if directory:
            sbs_files = scan_sbs_files(directory)
            aliases_examples = {}
            for file_path in sbs_files:
                file_aliases_examples = extract_aliases(file_path)
                for alias, examples in file_aliases_examples.items():
                    if alias not in aliases_examples:
                        aliases_examples[alias] = examples
                    else:
                        aliases_examples[alias].extend(examples)

            aliases_listbox.delete(0, tk.END)
            if aliases_examples:
                for alias in sorted(aliases_examples):
                    aliases_listbox.insert(tk.END, alias)

                # 更新 "识别出的aliases" 标签的文本
                aliases_label.config(text=f"已检测到 {len(sbs_files)} 个 sbs 文件，包含的 Aliases 有：")
            else:
                messagebox.showinfo("信息", "没有找到任何 aliases。")

    def on_alias_select(event):
        global selected_alias
        selection = aliases_listbox.curselection()
        if selection:
            index = selection[0]
            selected_alias = aliases_listbox.get(index)
            update_examples_text()
            on_new_alias_entry_change()  # 调用以更新 aliases 改名预览

    def update_examples_text():
        """
        根据选中的alias更新Aliases示例文本。
        """
        examples_text.delete(1.0, tk.END)
        if selected_alias:
            for file_path in sbs_files:
                if selected_alias in extract_aliases(file_path):
                    formatted_file_path = file_path.replace('\\', '/')
                    examples_text.insert(tk.END, f'"{formatted_file_path}"\n', 'file_path')
                    for example in extract_aliases(file_path)[selected_alias]:
                        examples_text.insert(tk.END, f'    {example}\n')
            examples_text.tag_configure('file_path', font=global_font_bold)

    def on_new_alias_entry_change(*args):
        global selected_alias, alias_change_step
        new_alias = new_alias_var.get()
        if selected_alias and new_alias:
            new_alias_preview.delete(1.0, tk.END)
            for file_path in sbs_files:
                file_aliases_examples = extract_aliases(file_path)
                if selected_alias in file_aliases_examples:
                    formatted_file_path = file_path.replace('\\', '/')
                    new_alias_preview.insert(tk.END, f'"{formatted_file_path}"\n', 'file_path')
                    for example in file_aliases_examples[selected_alias]:
                        alias_start = example.find(f'{selected_alias}://')
                        if alias_start != -1:
                            before_alias = example[:alias_start]
                            after_alias_start = alias_start + len(selected_alias) + 3  # +3 for '://'
                            after_alias = example[after_alias_start:]
                            # Apply alias change step
                            after_alias_step_applied = after_alias[max(0, alias_change_step):]
                            new_example = before_alias + new_alias + after_alias_step_applied
                            new_alias_preview.insert(tk.END, f'    {new_example}\n')

            # 配置文件路径的字体为加粗
            new_alias_preview.tag_configure('file_path', font=global_font_bold)

    def on_submit():
        new_alias = new_alias_var.get()
        if selected_alias and new_alias:
            # 确认操作弹窗
            total_files = len(sbs_files)
            if not messagebox.askyesno("确认", f"该操作会影响 {total_files} 个文件，确认继续吗？"):
                return

            success_count = 0
            failure_count = 0
            failure_messages = []

            # 对每个文件进行操作
            for file_path in sbs_files:
                success, error_message = modify_sbs_file(file_path, {selected_alias: new_alias})
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    failure_messages.append(f"文件：{file_path}，失败原因：{error_message}")

            # 显示操作结果
            success_message = f"成功修改 {success_count} 个文件。"
            failure_message = f"失败 {failure_count} 个文件。失败详情：\n" + "\n".join(
                failure_messages) if failure_count > 0 else ""
            messagebox.showinfo("完成", success_message + "\n" + failure_message)
            # 刷新别名列表
            refresh_aliases()

    def refresh_aliases():
        update_aliases_list()


    # 设置窗口背景为深色
    root = ThemedTk(theme="black")
    global_font_bold = font.nametofont("TkDefaultFont").copy()
    global_font_bold.configure(weight="bold")
    root.configure(bg="#333333")  # 设置窗口背景为深色
    root.title("SBS Aliases 修改器")
    new_alias_var = tk.StringVar()
    # 创建一个样式对象
    style = ttk.Style(root)

    # 配置按钮样式
    style.configure('TButton', anchor='center')  # 确保文本居中

    # 深色背景和浅色前景
    dark_background = "#333333"
    darker_background = "#1a1a1a"  # 更暗的背景色
    light_foreground = "#ffffff"
    border_color = "#1a1a1a"  # 设置边框颜色

    # 创建一个样式对象
    style = ttk.Style(root)
    # 配置 ttk.Entry 控件的样式
    style.configure("Dark.TEntry", background="#333333", foreground="#ffffff")


    # 扫描位置标签和输入框
    directory_frame = tk.Frame(root, bg=dark_background)
    directory_frame.pack(side='top', fill='x', padx=10, pady=5)

    directory_label = ttk.Label(directory_frame, text="扫描位置：", background="#333333", foreground="#ffffff")
    directory_label.pack(side='left')

    directory_var = tk.StringVar()
    directory_entry = tk.Entry(directory_frame, textvariable=directory_var, bg=darker_background,fg=light_foreground)
    directory_entry.pack(side='left', fill='x', expand=True, padx=5)

    # 扫描目录按钮
    choose_dir_button = ttk.Button(directory_frame, text="...", command=on_choose_directory)
    choose_dir_button.pack(side='right')

    # 刷新按钮
    refresh_button = ttk.Button(directory_frame, text="刷新", command=refresh_aliases)
    refresh_button.pack(side='right', padx=10)

    # 别名列表框

    aliases_label = ttk.Label(root, text="识别出的aliases：", background=dark_background, foreground=light_foreground)
    aliases_label.pack(side='top', fill='x', padx=10)


    aliases_frame = tk.Frame(root, bg=border_color)  # 设置 Frame 边框颜色
    aliases_frame.pack(side='top', fill='both', expand=True, padx=10, pady=5)

    aliases_listbox = Listbox(aliases_frame, bg=dark_background, fg=light_foreground, bd=1,
                             highlightthickness=0, relief="solid", borderwidth=1)
    aliases_listbox.pack(side='left', fill='both', expand=True)  # 添加内边距，使边框可见
    aliases_listbox.bind('<ButtonRelease-1>', on_alias_select)  # 绑定鼠标点击事件

    aliases_scrollbar = ttk.Scrollbar(aliases_frame, orient='vertical', command=aliases_listbox.yview)
    aliases_scrollbar.pack(side='right', fill='y')
    aliases_listbox.config(yscrollcommand=aliases_scrollbar.set)

    # 示例文本框及其滚动条
    examples_label = ttk.Label(root, text="Aliases 示例：", background=dark_background, foreground=light_foreground)
    examples_label.pack(side='top', fill='x', padx=10)

    examples_frame = tk.Frame(root, bg=dark_background)
    examples_frame.pack(side='top', fill='x', padx=10, pady=5)

    examples_text = Text(examples_frame, bg=dark_background, fg=light_foreground, bd=1, highlightthickness=0,
                         relief="solid", borderwidth=1)  # 设置 relief 为 solid
    examples_text.pack(side='left', fill='both', expand=True, padx=2, pady=2)

    examples_scrollbar = ttk.Scrollbar(examples_frame, orient='vertical', command=examples_text.yview)
    examples_scrollbar.pack(side='right', fill='y')
    examples_text.config(yscrollcommand=examples_scrollbar.set)

    # 新别名输入框、-和+按钮的框架
    alias_input_frame = tk.Frame(root, bg=dark_background)
    alias_input_frame.pack(side='top', fill='x', padx=10, pady=5)
    # 新别名输入框和标签
    new_alias_label = ttk.Label(alias_input_frame, text="自定义aliases输入：", background="#333333",
                                foreground="#ffffff")
    new_alias_label.pack(side='left')

    new_alias_var = tk.StringVar()
    new_alias_var.trace_add("write", on_new_alias_entry_change)

    new_alias_entry = tk.Entry(alias_input_frame, textvariable=new_alias_var, bg=darker_background, fg=light_foreground)
    new_alias_entry.pack(side='left', fill='x', expand=True, padx=5)


    # 新别名预览文本框及其滚动条
    new_alias_preview_label = ttk.Label(root, text="Aliases 改名预览：", background=dark_background,
                                        foreground=light_foreground)
    new_alias_preview_label.pack(side='top', fill='x', padx=10)

    new_alias_preview_frame = tk.Frame(root, bg=dark_background)  # 移除边框颜色设置
    new_alias_preview_frame.pack(side='top', fill='x', padx=10, pady=5)

    new_alias_preview = Text(new_alias_preview_frame, bg=dark_background, fg=light_foreground, bd=1,
                             highlightthickness=0, relief="solid", borderwidth=1)  # 设置 relief 为 solid
    new_alias_preview.pack(side='left', fill='both', expand=True)

    new_alias_preview_scrollbar = ttk.Scrollbar(new_alias_preview_frame, orient='vertical',
                                                command=new_alias_preview.yview)
    new_alias_preview_scrollbar.pack(side='right', fill='y')
    new_alias_preview.config(yscrollcommand=new_alias_preview_scrollbar.set)

    # 提交按钮
    submit_button = ttk.Button(root, text="提交", command=on_submit)
    submit_button.pack(padx=10, pady=10)


    root.mainloop()

# 启动GUI
create_gui()
