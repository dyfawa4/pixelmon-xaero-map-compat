from pathlib import Path
import queue,threading,tkinter as tk
from tkinter import ttk,filedialog,messagebox
from install_core import find_java,install

def show_installer(parent):
    window=tk.Toplevel(parent);window.title('生成宝可梦定制 Xaero 组件');window.geometry('820x480');window.minsize(720,450)
    body=ttk.Frame(window,padding=20);body.pack(fill='both',expand=True);body.columnconfigure(1,weight=1)
    ttk.Label(body,text='安装地图组件',font=('Microsoft YaHei UI',17,'bold')).grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,10))
    ttk.Label(body,text='从作者官方 Modrinth 文件生成相同的定制原生组件，不额外增加兼容模组。\n生成到独立文件夹后，退出游戏，将三个 JAR 放入游戏 mods，并移走旧地图组件。',wraplength=760).grid(row=1,column=0,columnspan=3,sticky='w',pady=(0,16))
    java=tk.StringVar(value=str(find_java() or ''));output=tk.StringVar(value=str(Path.home()/'Downloads/宝可梦地图组件'));originals=tk.StringVar()
    def browse_file():
        result=filedialog.askopenfilename(parent=window,title='选择 Java 11+ 的 java.exe',filetypes=[('Java','java.exe'),('所有文件','*')])
        if result:java.set(result)
    def browse(var):
        result=filedialog.askdirectory(parent=window,title='选择文件夹')
        if result:var.set(result)
    for row,title,var,command in [(2,'Java 程序',java,browse_file),(3,'组件输出目录',output,lambda:browse(output)),(4,'已有官方原版（可选）',originals,lambda:browse(originals))]:
        ttk.Label(body,text=title).grid(row=row,column=0,sticky='w',padx=(0,10),pady=6)
        ttk.Entry(body,textvariable=var).grid(row=row,column=1,sticky='ew',pady=6)
        ttk.Button(body,text='选择…',command=command).grid(row=row,column=2,padx=(8,0))
    ttk.Label(body,text='留空“已有官方原版”时联网下载固定版本；选择原版目录可离线生成。\n所需版本：小地图 26.6.0、世界地图 1.47.0、XaeroLib 1.7.3，均为 Forge 1.16.5。',wraplength=760).grid(row=5,column=0,columnspan=3,sticky='w',pady=10)
    state=tk.StringVar(value='准备就绪。需要 Java 11 或更高版本；无需安装 Python。')
    ttk.Label(body,textvariable=state,wraplength=760).grid(row=6,column=0,columnspan=3,sticky='w',pady=10)
    messages=queue.Queue();busy=[False]
    def execute():
        if not java.get() or not output.get():messagebox.showerror('信息不完整','请选择 Java 和输出目录。',parent=window);return
        params=(Path(output.get()),Path(java.get()),Path(originals.get()) if originals.get() else None)
        busy[0]=True;button.configure(state='disabled')
        def worker():
            try:messages.put(('done',install(*params,progress=lambda s:messages.put(('status',s)))))
            except Exception as error:messages.put(('error',str(error)))
        threading.Thread(target=worker,daemon=True).start();window.after(100,poll)
    def poll():
        while not messages.empty():
            kind,value=messages.get()
            if kind=='status':state.set(value)
            elif kind=='done':
                busy[0]=False;button.configure(state='normal');state.set('生成完成：'+value['output'])
                messagebox.showinfo('地图组件已生成','已生成：\n'+'\n'.join(value['files'])+'\n\n请退出游戏，将这三个 JAR 复制到实例 mods，移走旧 Xaero 与 JourneyMap，再进入对应世界一次。随后可使用主窗口迁移坐标点。',parent=window)
            else:busy[0]=False;button.configure(state='normal');state.set('未完成。');messagebox.showerror('生成失败',value,parent=window)
        if busy[0]:window.after(100,poll)
    button=ttk.Button(body,text='生成地图组件',command=execute);button.grid(row=7,column=2,pady=12,sticky='e')
    def close():
        if busy[0]:messagebox.showinfo('正在生成','请等待当前操作完成后关闭。',parent=window)
        else:window.destroy()
    window.protocol('WM_DELETE_WINDOW',close)
    return window
