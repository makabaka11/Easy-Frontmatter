import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
import os
import re


def toml_escape(value):
    s = str(value).replace("'", "\\'")
    return f"'{s}'"


def build_toml_frontmatter(data):
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
    return text.startswith('+++\n') or text.startswith('+++\r\n')


def replace_or_prepend_frontmatter(md_text, frontmatter_text):
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
    pattern = r"^\+\+\+\s*\n(.*?)\n\+\+\+"
    m = re.search(pattern, text, flags=re.DOTALL)
    if not m:
        return {}
    fm_text = m.group(1)
    data = {}
    # 简单解析 key = value 形式
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        key, val = [x.strip() for x in line.split('=', 1)]
        # 解析布尔、数字、字符串、数组
        if val.lower() == 'true':
            data[key] = True
        elif val.lower() == 'false':
            data[key] = False
        elif val.startswith('['):
            arr = re.findall(r"'([^']*)'", val)
            data[key] = arr
        elif val.startswith("'") and val.endswith("'"):
            data[key] = val[1:-1]
        else:
            data[key] = val
    return data


class FrontmatterGUI:
    def __init__(self, master):
        master.title('Markdown Frontmatter 编辑器（中文）')
        master.geometry('720x540')

        self.file_path = tk.StringVar()

        # 文件选择
        top = ttk.Frame(master, padding=8)
        top.pack(fill='x')
        ttk.Label(top, text='Markdown 文件:').pack(side='left')
        ttk.Entry(top, textvariable=self.file_path).pack(side='left', fill='x', expand=True, padx=6)
        ttk.Button(top, text='浏览', command=self.browse_file).pack(side='left')

        # 基础信息
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

        # 分类
        cat_frame = ttk.Labelframe(main, text='分类 (Categories)', padding=6)
        cat_frame.pack(fill='both', expand=True, pady=8)
        self.cat_container = ttk.Frame(cat_frame)
        self.cat_container.pack(fill='x')
        ttk.Button(cat_frame, text='添加分类 +', command=self.add_category).pack(pady=4)
        self.category_entries = []

        # 权重与草稿
        w_frame = ttk.Frame(main)
        w_frame.pack(fill='x', pady=6)
        ttk.Label(w_frame, text='权重 (weight):').pack(side='left')
        self.weight_entry = ttk.Entry(w_frame, width=10)
        self.weight_entry.pack(side='left', padx=6)
        self.draft_var = tk.BooleanVar()
        ttk.Checkbutton(w_frame, text='草稿 (draft)', variable=self.draft_var).pack(side='left', padx=12)

        # 底部按钮
        bottom = ttk.Frame(master, padding=8)
        bottom.pack(fill='x')
        ttk.Button(bottom, text='预览 Frontmatter', command=self.preview).pack(side='left')
        ttk.Button(bottom, text='保存到文件', command=self.save_to_file).pack(side='right')

    def browse_file(self):
        p = filedialog.askopenfilename(filetypes=[('Markdown 文件', '*.md'), ('所有文件', '*.*')])
        if p:
            self.file_path.set(p)
            self.load_existing_frontmatter(p)

    def load_existing_frontmatter(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                txt = f.read()
            if has_toml_frontmatter(txt):
                data = parse_toml_frontmatter(txt)
                # 填充界面
                self.title_entry.delete(0, 'end')
                self.title_entry.insert(0, data.get('title', ''))
                self.date_entry.delete(0, 'end')
                self.date_entry.insert(0, data.get('date', ''))
                self.desc_entry.delete(0, 'end')
                self.desc_entry.insert(0, data.get('description', ''))
                self.image_entry.delete(0, 'end')
                self.image_entry.insert(0, data.get('image', ''))
                self.weight_entry.delete(0, 'end')
                self.weight_entry.insert(0, data.get('weight', ''))
                self.draft_var.set(data.get('draft', False))
                # 分类
                for e in list(self.category_entries):
                    self.remove_category(e.master)
                cats = data.get('categories', [])
                for c in cats:
                    self.add_category(c)
        except Exception as e:
            messagebox.showerror('错误', f'读取 frontmatter 失败: {e}')

    def set_now(self):
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        self.date_entry.delete(0, 'end')
        self.date_entry.insert(0, now.isoformat())

    def add_category(self, text=''):
        frame = ttk.Frame(self.cat_container)
        entry = ttk.Entry(frame)
        entry.insert(0, text)
        entry.pack(side='left', fill='x', expand=True)
        ttk.Button(frame, text='-', width=3, command=lambda: self.remove_category(frame)).pack(side='left', padx=4)
        frame.pack(fill='x', pady=2)
        self.category_entries.append(entry)

    def remove_category(self, frame):
        for e in self.category_entries:
            if e.master == frame:
                self.category_entries.remove(e)
        frame.destroy()

    def collect_data(self):
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