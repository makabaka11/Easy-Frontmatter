import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
import os
import re


def toml_escape(value):
    """转义值，统一用单引号包裹（TOML 单双引号都支持）"""
    s = str(value).replace("'", "\\'")
    return f"'{s}'"


def build_toml_frontmatter(data):
    """构建 TOML 格式的 frontmatter"""
    lines = ['+++']
    lines.append(f"title = {toml_escape(data['title'])}")
    lines.append(f"date = {data['date']}")
    if data.get('description'):
        lines.append(f"description = {toml_escape(data['description'])}")
    if data.get('weight'):
        lines.append(f"weight = {data['weight']}")
    if data.get('draft'):
        lines.append(f"draft = true")
    if data.get('image'):
        lines.append(f"image = {toml_escape(data['image'])}")
    if data.get('categories'):
        lines.append('categories = [')
        for c in data['categories']:
            lines.append(f"    {toml_escape(c)},")
        lines.append(']  ')
    lines.append('+++\n')
    return '\n'.join(lines)


def has_toml_frontmatter(text):
    """判断是否包含 TOML frontmatter"""
    return text.startswith('+++\n') or text.startswith('+++\r\n')


def replace_or_prepend_frontmatter(md_text, frontmatter_text):
    """替换或前置 frontmatter"""
    if has_toml_frontmatter(md_text):
        pattern = r"^\+\+\+\s*\n.*?\n^\+\+\+\s*\n"
        m = re.search(pattern, md_text, flags=re.DOTALL | re.MULTILINE)
        if m:
            rest = md_text[m.end():]
            return frontmatter_text + rest.lstrip('\n')
        else:
            return frontmatter_text + md_text
    else:
        return frontmatter_text + md_text


def parse_toml_frontmatter(text):
    """
    解析 TOML frontmatter（支持单双引号、多行数组）
    核心改进：同时匹配单引号(')和双引号(")的内容
    """
    pattern = r"^\+\+\+\s*\n(.*?)\n\+\+\+"
    m = re.search(pattern, text, flags=re.DOTALL)
    if not m:
        return {}

    fm_lines = m.group(1).splitlines()
    data = {}
    i = 0
    len_lines = len(fm_lines)

    while i < len_lines:
        line = fm_lines[i].strip()
        i += 1

        # 跳过空行和注释
        if not line or line.startswith('#'):
            continue

        # 处理 key=value 格式
        if '=' not in line:
            continue

        key, val = [x.strip() for x in line.split('=', 1)]

        # 处理多行数组（以[开头但没有]结尾）
        if val.startswith('[') and not val.endswith(']'):
            # 继续读取后续行直到找到]
            while i < len_lines:
                next_line = fm_lines[i].strip()
                i += 1
                val += next_line
                if ']' in next_line:
                    break

        # 解析值的类型
        if val.lower() == 'true':
            data[key] = True
        elif val.lower() == 'false':
            data[key] = False
        elif val.startswith('['):
            # 关键：匹配单引号或双引号包裹的内容（正则分组捕获）
            # 正则解释：(['"]) 匹配单/双引号，(.*?) 非贪婪匹配内容，\1 反向引用匹配的引号
            categories = re.findall(r"(['\"])(.*?)\1", val)
            # 提取引号内的内容（忽略引号本身）
            data[key] = [cat.strip() for (_, cat) in categories if cat.strip()]
        elif val.startswith(("'", '"')) and val.endswith(("'", '"')):
            # 处理单/双引号包裹的单个值：去掉首尾引号
            data[key] = val[1:-1].strip()
        else:
            # 处理数字、日期等原始值
            data[key] = val.strip()

    return data


class FrontmatterGUI:
    def __init__(self, master):
        master.title('Markdown Frontmatter 编辑器（支持单双引号）')
        master.geometry('720x540')

        self.file_path = tk.StringVar()

        # 文件选择区域
        top = ttk.Frame(master, padding=8)
        top.pack(fill='x')
        ttk.Label(top, text='Markdown 文件:').pack(side='left')
        ttk.Entry(top, textvariable=self.file_path).pack(side='left', fill='x', expand=True, padx=6)
        ttk.Button(top, text='浏览', command=self.browse_file).pack(side='left')

        # 基础信息区域
        main = ttk.Frame(master, padding=8)
        main.pack(fill='both', expand=True)

        ttk.Label(main, text='标题（必填）:').pack(anchor='w')
        self.title_entry = ttk.Entry(main)
        self.title_entry.pack(fill='x', pady=4)

        ttk.Label(main, text='日期（必填）:').pack(anchor='w')
        date_frame = ttk.Frame(main)
        date_frame.pack(fill='x')
        self.date_entry = ttk.Entry(date_frame)
        self.date_entry.pack(side='left', fill='x', expand=True)
        ttk.Button(date_frame, text='当前时间', command=self.set_now).pack(side='left', padx=6)

        ttk.Label(main, text='描述:').pack(anchor='w')
        self.desc_entry = ttk.Entry(main)
        self.desc_entry.pack(fill='x', pady=4)

        ttk.Label(main, text='头图路径:').pack(anchor='w')
        self.image_entry = ttk.Entry(main)
        self.image_entry.pack(fill='x', pady=4)

        # 分类区域
        cat_frame = ttk.Labelframe(main, text='分类 (Categories)', padding=6)
        cat_frame.pack(fill='both', expand=True, pady=8)
        self.cat_container = ttk.Frame(cat_frame)
        self.cat_container.pack(fill='x')
        ttk.Button(cat_frame, text='添加分类 +', command=self.add_category).pack(pady=4)
        self.category_entries = []

        # 权重与草稿区域
        w_frame = ttk.Frame(main)
        w_frame.pack(fill='x', pady=6)
        ttk.Label(w_frame, text='权重 (weight):').pack(side='left')
        self.weight_entry = ttk.Entry(w_frame, width=10)
        self.weight_entry.pack(side='left', padx=6)
        self.draft_var = tk.BooleanVar()
        ttk.Checkbutton(w_frame, text='草稿 (draft)', variable=self.draft_var).pack(side='left', padx=12)

        # 底部按钮区域
        bottom = ttk.Frame(master, padding=8)
        bottom.pack(fill='x')
        ttk.Button(bottom, text='预览 Frontmatter', command=self.preview).pack(side='left')
        ttk.Button(bottom, text='保存到文件', command=self.save_to_file).pack(side='right')

    def browse_file(self):
        """选择文件并加载内容"""
        p = filedialog.askopenfilename(filetypes=[('Markdown 文件', '*.md'), ('所有文件', '*.*')])
        if p:
            self.file_path.set(p)
            self.clear_all_fields()  # 清除现有内容
            self.load_existing_frontmatter(p)  # 加载新文件

    def clear_all_fields(self):
        """清除所有输入框内容（包括分类）"""
        self.title_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.desc_entry.delete(0, tk.END)
        self.image_entry.delete(0, tk.END)
        self.weight_entry.delete(0, tk.END)
        self.draft_var.set(False)

        # 销毁所有分类输入框并清空列表
        for entry in self.category_entries:
            entry.master.destroy()
        self.category_entries = []

    def load_existing_frontmatter(self, path):
        """加载文件中的 frontmatter 并填充到界面"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                txt = f.read()

            if has_toml_frontmatter(txt):
                data = parse_toml_frontmatter(txt)

                # 填充基础信息
                self.title_entry.insert(0, data.get('title', ''))
                self.date_entry.insert(0, data.get('date', ''))
                self.desc_entry.insert(0, data.get('description', ''))
                self.image_entry.insert(0, data.get('image', ''))
                self.weight_entry.insert(0, data.get('weight', ''))
                self.draft_var.set(data.get('draft', False))

                # 加载分类：有多少个分类就创建多少个文本框
                categories = data.get('categories', [])
                for cat in categories:
                    self.add_category(cat)

        except Exception as e:
            messagebox.showerror('错误', f'读取 frontmatter 失败: {e}')

    def set_now(self):
        """设置当前时间为日期值"""
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, now.isoformat())

    def add_category(self, text=''):
        """添加分类输入框（支持初始文本）"""
        frame = ttk.Frame(self.cat_container)
        entry = ttk.Entry(frame)
        if text:
            entry.insert(0, text)
        entry.pack(side='left', fill='x', expand=True)
        ttk.Button(frame, text='-', width=3, command=lambda: self.remove_category(frame)).pack(side='left', padx=4)
        frame.pack(fill='x', pady=2)
        self.category_entries.append(entry)

    def remove_category(self, frame):
        """移除指定的分类行"""
        for entry in self.category_entries:
            if entry.master == frame:
                self.category_entries.remove(entry)
                break
        frame.destroy()

    def collect_data(self):
        """收集界面中的所有输入数据"""
        cats = [e.get().strip() for e in self.category_entries if e.get().strip()]
        return {
            'title': self.title_entry.get().strip(),
            'date': self.date_entry.get().strip(),
            'description': self.desc_entry.get().strip(),
            'image': self.image_entry.get().strip(),
            'categories': cats,
            'weight': self.weight_entry.get().strip(),
            'draft': self.draft_var.get()
        }

    def preview(self):
        """预览生成的 frontmatter"""
        d = self.collect_data()
        if not d['title'] or not d['date']:
            messagebox.showerror('错误', '标题和日期为必填项！')
            return
        fm = build_toml_frontmatter(d)
        win = tk.Toplevel()
        win.title('Frontmatter 预览')
        txt = tk.Text(win, wrap='none', width=80, height=20)
        txt.insert('1.0', fm)
        txt.configure(state='disabled')
        txt.pack(fill='both', expand=True)
        ttk.Button(win, text='关闭', command=win.destroy).pack()

    def save_to_file(self):
        """将 frontmatter 保存到文件"""
        p = self.file_path.get().strip()
        if not p:
            messagebox.showerror('错误', '请先选择 Markdown 文件！')
            return
        d = self.collect_data()
        if not d['title'] or not d['date']:
            messagebox.showerror('错误', '标题和日期为必填项！')
            return
        fm = build_toml_frontmatter(d)
        try:
            with open(p, 'r', encoding='utf-8') as f:
                original = f.read()
            new_text = replace_or_prepend_frontmatter(original, fm)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(new_text)
            messagebox.showinfo('成功', 'Frontmatter 已保存！')
        except Exception as e:
            messagebox.showerror('错误', f'保存失败: {e}')


if __name__ == '__main__':
    root = tk.Tk()
    app = FrontmatterGUI(root)
    root.mainloop()