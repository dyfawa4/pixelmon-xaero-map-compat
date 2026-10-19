"""Portable Chinese desktop UI. No Minecraft, Java or Python install required in EXE."""
from pathlib import Path
import argparse, json, os, sys, tkinter as tk
from tkinter import ttk, filedialog, messagebox
if not getattr(sys,'frozen',False):sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'installer'))
from migrate_core import (VERSION,discover_sources,discover_targets,source_files,read_point,
                          destinations,make_plan,apply_plan,restore_backup,backup_root)

class App:
    def __init__(self, root):
        self.root=root;self.plan=None;self.result=None;self.mapping_vars={};self.sources=[];self.targets=[]
        root.title('宝可梦地图工具 · 安装与坐标迁移 '+VERSION)
        root.geometry('1080x850');root.minsize(920,740)
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('.',font=('Microsoft YaHei UI',10))
        style.configure('Title.TLabel',font=('Microsoft YaHei UI',17,'bold'))
        style.configure('Treeview',rowheight=28)
        body=ttk.Frame(root,padding=18);body.pack(fill='both',expand=True)
        ttk.Label(body,text='把你的旅行地图坐标点带到 Xaero',style='Title.TLabel').pack(anchor='w')
        from install_ui import show_installer
        ttk.Button(body,text='安装 / 生成宝可梦地图组件…',command=lambda:show_installer(root)).pack(anchor='e')
        ttk.Label(body,text='支持普通坐标点、历史死亡点与多维度。原旅行地图文件保持完整；本版不转换已探索地形。',wraplength=1000).pack(anchor='w',pady=(6,14))
        self.src_path=tk.StringVar(value=str(Path.cwd()));self.dst_path=tk.StringVar(value=str(Path.cwd()))
        self.source_choice=tk.StringVar();self.target_choice=tk.StringVar();self.deaths=tk.BooleanVar(value=True);self.closed=tk.BooleanVar(value=False)
        box=ttk.LabelFrame(body,text='1  选择来源与目标',padding=10);box.pack(fill='x')
        box.columnconfigure(1,weight=1)
        for row,title,var,command in [(0,'旅行地图所在目录',self.src_path,self.scan_source),(2,'Xaero 所在目录',self.dst_path,self.scan_target)]:
            ttk.Label(box,text=title).grid(row=row,column=0,sticky='w',padx=(0,10),pady=4)
            entry=ttk.Entry(box,textvariable=var);entry.grid(row=row,column=1,sticky='ew',pady=4)
            var.trace_add('write',lambda *_,r=row:self.path_changed(r))
            ttk.Button(box,text='浏览…',command=lambda v=var,c=command:self.browse(v,c)).grid(row=row,column=2,padx=6)
            ttk.Button(box,text='扫描',command=command).grid(row=row,column=3)
        ttk.Label(box,text='来源世界 / 服务器').grid(row=1,column=0,sticky='w')
        self.source_combo=ttk.Combobox(box,textvariable=self.source_choice,state='readonly');self.source_combo.grid(row=1,column=1,columnspan=3,sticky='ew',pady=5)
        ttk.Label(box,text='目标世界 / 服务器').grid(row=3,column=0,sticky='w')
        self.target_combo=ttk.Combobox(box,textvariable=self.target_choice,state='readonly');self.target_combo.grid(row=3,column=1,columnspan=3,sticky='ew',pady=5)
        for combo in [self.source_combo,self.target_combo]: combo.bind('<<ComboboxSelected>>',lambda _:self.refresh_mapping())
        ttk.Label(box,text='可选择游戏实例、.minecraft 或 JourneyMap 的单个世界目录。目标需先使用本定制版进入对应世界一次，再退出游戏。',wraplength=980).grid(row=4,column=0,columnspan=4,sticky='w',pady=(6,0))
        mapping=ttk.LabelFrame(body,text='2  维度对应',padding=10);mapping.pack(fill='x',pady=(12,0))
        self.mapping_frame=ttk.Frame(mapping);self.mapping_frame.pack(fill='x')
        self.mapping_frame.columnconfigure(1,weight=1)
        self.mapping_note=ttk.Label(self.mapping_frame,text='选择来源和目标后显示。多个子世界时必须明确选择，避免串服。');self.mapping_note.grid(sticky='w')
        options=ttk.Frame(body);options.pack(fill='x',pady=10)
        ttk.Checkbutton(options,text='包含历史死亡点',variable=self.deaths,command=self.invalidate).pack(side='left')
        ttk.Button(options,text='生成预览',command=self.preview).pack(side='right')
        self.summary=tk.StringVar(value='请选择同一个存档或服务器的来源和目标，然后生成预览。')
        ttk.Label(body,textvariable=self.summary,wraplength=1000).pack(anchor='w',pady=(0,7))
        table=ttk.Frame(body);table.pack(fill='both',expand=True)
        columns=('status','name','dimension','coordinates','kind','enabled')
        self.tree=ttk.Treeview(table,columns=columns,show='headings',height=8)
        for key,label,width in zip(columns,['处理','名称','维度','坐标 X / Y / Z','类型','显示'],[75,210,200,160,90,60]):
            self.tree.heading(key,text=label);self.tree.column(key,width=width,minwidth=60,stretch=key in ('name','dimension'))
        self.tree.grid(row=0,column=0,sticky='nsew');table.columnconfigure(0,weight=1);table.rowconfigure(0,weight=1)
        scroll=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview);scroll.grid(row=0,column=1,sticky='ns');self.tree.configure(yscrollcommand=scroll.set)
        bottom=ttk.Frame(body);bottom.pack(before=table,fill='x',pady=(12,0))
        ttk.Checkbutton(bottom,text='我已完全退出目标游戏',variable=self.closed,command=self.update_buttons).pack(side='left')
        self.report_button=ttk.Button(bottom,text='导出报告',command=self.report,state='disabled');self.report_button.pack(side='right',padx=(8,0))
        self.apply_button=ttk.Button(bottom,text='导入坐标点',command=self.apply,state='disabled');self.apply_button.pack(side='right',padx=(8,0))
        self.restore_button=ttk.Button(bottom,text='恢复迁移前备份…',command=self.restore);self.restore_button.pack(side='right')
        ttk.Label(body,text='导入会先自动备份目标文件。重复项按名称、坐标及类型去重；现有点位和分组保持原样。',wraplength=1000).pack(anchor='w',pady=(10,0))
        self.update_buttons()

    def fail(self,error): messagebox.showerror('操作未完成',str(error),parent=self.root)
    def invalidate(self,*_):
        self.plan=None;self.result=None
        if hasattr(self,'tree'): self.tree.delete(*self.tree.get_children());self.summary.set('选项已改变，请重新生成预览。');self.update_buttons()
    def path_changed(self,row):
        if row==0:self.sources=[];self.source_choice.set('');self.source_combo['values']=[]
        else:self.targets=[];self.target_choice.set('');self.target_combo['values']=[]
        self.invalidate()
    def browse(self,var,scan):
        folder=filedialog.askdirectory(parent=self.root,title='选择目录',initialdir=var.get() if Path(var.get()).is_dir() else str(Path.home()))
        if folder:var.set(folder);scan()
    def scan_source(self):
        try:
            self.sources=discover_sources(Path(self.src_path.get()));self.source_combo['values']=[str(p) for p in self.sources]
            self.source_choice.set(str(self.sources[0]) if len(self.sources)==1 else '')
            self.refresh_mapping()
            if not self.sources:messagebox.showinfo('未找到旅行地图坐标点','请选到包含 journeymap 的游戏实例目录，或直接选择 journeymap/data/sp 或 mp 下的单个世界目录。',parent=self.root)
        except Exception as e:self.fail(e)
    def scan_target(self):
        try:
            self.targets=discover_targets(Path(self.dst_path.get()));self.target_combo['values']=[str(p) for p in self.targets]
            self.target_choice.set(str(self.targets[0]) if len(self.targets)==1 else '')
            self.refresh_mapping()
            if not self.targets:messagebox.showinfo('未找到 Xaero 世界','请先用定制 Xaero 进入对应存档或服务器一次，完全退出游戏，再扫描实际游戏实例目录。\n本工具适配 xaero/minimap 目录格式。',parent=self.root)
        except Exception as e:self.fail(e)
    def refresh_mapping(self):
        self.invalidate();self.mapping_vars={}
        for w in self.mapping_frame.winfo_children():w.destroy()
        if not self.source_choice.get() or not self.target_choice.get():
            ttk.Label(self.mapping_frame,text='请先明确选择来源与目标。').grid(sticky='w');return
        try:
            dims=set();errors=0
            for f in source_files(Path(self.source_choice.get())):
                try:dims.update(p.dimension for p in read_point(f))
                except (ValueError,UnicodeError,KeyError,TypeError):errors+=1
            for row,dim in enumerate(sorted(dims)):
                ttk.Label(self.mapping_frame,text=dim).grid(row=row,column=0,sticky='w',padx=(0,12),pady=3)
                choices=destinations(Path(self.target_choice.get()),dim);var=tk.StringVar(value=choices[0] if len(choices)==1 else '请选择目标子世界')
                combo=ttk.Combobox(self.mapping_frame,textvariable=var,values=choices+['不导入此维度'],state='readonly');combo.grid(row=row,column=1,sticky='ew',pady=3)
                var.trace_add('write',self.invalidate);self.mapping_vars[dim]=var
            if not dims:ttk.Label(self.mapping_frame,text='未发现可读取的坐标点；生成预览查看错误报告。').grid(sticky='w')
        except Exception as e:self.fail(e)
    def update_buttons(self):
        if not hasattr(self,'apply_button'):return
        can=self.plan and not self.result and bool(self.plan.writes) and self.closed.get()
        self.apply_button.configure(state='normal' if can else 'disabled')
        self.report_button.configure(state='normal' if self.plan else 'disabled')
        self.restore_button.configure(state='normal' if self.closed.get() else 'disabled')
    def preview(self):
        try:
            if not self.source_choice.get() or not self.target_choice.get():raise ValueError('请先选择来源世界和目标世界。')
            mappings={}
            for dim,var in self.mapping_vars.items():
                if var.get()=='请选择目标子世界':raise ValueError('请为 '+dim+' 选择子世界。')
                mappings[dim]='' if var.get()=='不导入此维度' else var.get()
            self.plan=make_plan(Path(self.source_choice.get()),Path(self.target_choice.get()),mappings,self.deaths.get());self.result=None
            self.tree.delete(*self.tree.get_children())
            for r in self.plan.rows:self.tree.insert('',tk.END,values=(r['status'],r['name'],r['dimension'],f"{r['x']} / {r['y']} / {r['z']}",'历史死亡点' if r['death'] else '坐标点','关闭' if r['disabled'] else '开启'))
            s=self.plan.summary();self.summary.set(f"预览：新增 {s['add']} 个（含死亡点 {s['deathpoints']}），已存在 {s['duplicates']} 个，不导入 {s['excluded']} 个；异常源文件 {len(s['issues'])} 个。将修改 {s['filesToChange']} 个文件。")
            self.update_buttons()
            if s['issues']:messagebox.showwarning('部分源文件无法转换','以下文件不会导入，其余有效坐标点可按预览导入：\n\n'+'\n'.join(s['issues'][:12])+ ('\n……完整列表可导出报告。' if len(s['issues'])>12 else ''),parent=self.root)
        except Exception as e:self.invalidate();self.fail(e)
    def apply(self):
        try:
            if not self.closed.get() or not self.plan:raise ValueError('请退出目标游戏并生成预览。')
            self.result=apply_plan(self.plan);self.apply_button.configure(state='disabled')
            self.summary.set(f"导入完成：{self.result['add']} 个。备份：{self.result['backup']}")
            messagebox.showinfo('迁移完成',f"已导入 {self.result['add']} 个坐标点。\n现在可启动对应游戏世界，在 Xaero 默认路径点分组查看。\n\n备份：{self.result['backup']}\n原旅行地图文件未修改。",parent=self.root)
        except Exception as e:self.fail(e)
    def report(self):
        if not self.plan:return
        filename=filedialog.asksaveasfilename(parent=self.root,title='保存迁移报告',defaultextension='.json',initialfile='坐标迁移报告.json',filetypes=[('JSON 报告','*.json')])
        if filename:Path(filename).write_text(json.dumps({'preview':self.plan.summary(),'result':self.result},ensure_ascii=False,indent=2),'utf8')
    def restore(self):
        try:
            initial=backup_root(Path(self.target_choice.get())) if self.target_choice.get() else Path.cwd()
            folder=filedialog.askdirectory(parent=self.root,title='选择含 manifest.json 的单次迁移备份目录',initialdir=str(initial) if initial.is_dir() else str(Path.cwd()))
            if not folder:return
            manifest=json.loads((Path(folder)/'manifest.json').read_text('utf8'))
            if not messagebox.askyesno('恢复迁移前备份',f"将恢复以下目标的 {len(manifest['entries'])} 个坐标点文件：\n{manifest['target']}\n\n若迁移后文件已有变化，工具会拒绝恢复，避免丢失新增点位。\n继续恢复？",parent=self.root):return
            result=restore_backup(Path(folder));self.invalidate();self.summary.set('已恢复迁移前文件：'+result['target'])
            messagebox.showinfo('恢复完成','已恢复 '+str(result['files'])+' 个文件。',parent=self.root)
        except Exception as e:self.fail(e)

def main():
    parser=argparse.ArgumentParser(description='JourneyMap → Xaero 坐标点迁移工具')
    parser.add_argument('--self-test',action='store_true');parser.add_argument('--source',type=Path);parser.add_argument('--target',type=Path);parser.add_argument('--apply',action='store_true');parser.add_argument('--report',type=Path)
    parser.add_argument('--install-output',type=Path);parser.add_argument('--java',type=Path);parser.add_argument('--originals',type=Path)
    args=parser.parse_args()
    if args.install_output:
        from install_core import install,find_java
        java=args.java or find_java()
        if java is None:parser.error('未找到 Java 11+，请通过 --java 指定 java.exe')
        result=install(args.install_output,java,args.originals)
        if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
        return
    if args.source or args.target:
        if not(args.source and args.target):parser.error('--source 与 --target 必须一起使用')
        plan=make_plan(args.source,args.target);result={'preview':plan.summary()}
        if args.apply:result['result']=apply_plan(plan)
        if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
        return
    root=tk.Tk();app=App(root)
    if args.self_test:
        root.withdraw();root.update_idletasks();assert str(app.apply_button['state'])=='disabled'
        from install_ui import show_installer
        window=show_installer(root);window.withdraw();root.update_idletasks();window.destroy();root.destroy();return
    root.mainloop()

if __name__=='__main__':main()
