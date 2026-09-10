"""Native desktop control panel; no hosted UI service or web subscription."""
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from .core import Store, runtime_root
from .run import REPO

def main():
    root=tk.Tk();root.title('Kort • Assistant Studio');root.geometry('1100x760');root.configure(bg='#111820')
    style=ttk.Style();style.theme_use('clam')
    style.configure('.',background='#18232e',foreground='#eef2f7',fieldbackground='#223344',font=('Segoe UI',11))
    style.configure('Treeview',background='#18232e',foreground='#eef2f7',fieldbackground='#18232e',rowheight=30)
    style.configure('TButton',padding=9);style.map('Treeview',background=[('selected','#526b82')])
    tk.Label(root,text='KORT / ASSISTANT STUDIO',bg='#111820',fg='#e9be70',font=('Segoe UI',21,'bold')).pack(anchor='w',padx=24,pady=(20,3))
    tk.Label(root,text='Cloud leadership • Local workers • Your knowledge',bg='#111820',fg='#a5b5c6').pack(anchor='w',padx=26,pady=(0,15))
    tabs=ttk.Notebook(root);tabs.pack(fill='both',expand=True,padx=22,pady=10)
    work=ttk.Frame(tabs,padding=14);knowledge=ttk.Frame(tabs,padding=14);settings=ttk.Frame(tabs,padding=14)
    tabs.add(work,text=' Tasks & evidence ');tabs.add(knowledge,text=' Knowledge ');tabs.add(settings,text=' Workers & setup ')
    bar=ttk.Frame(work);bar.pack(fill='x')
    project=tk.StringVar(value='game')
    ttk.Combobox(bar,textvariable=project,values=['personal','business','game'],state='readonly',width=12).pack(side='left')
    subproject=ttk.Entry(bar,width=14);subproject.insert(0,'subproject')
    subproject.pack(side='left',padx=(10,0))
    goal=ttk.Entry(bar);goal.pack(side='left',fill='x',expand=True,padx=10)
    table=ttk.Treeview(work,columns=('project','status','goal'),show='headings',height=8)
    for c,w in [('project',100),('status',150),('goal',630)]:table.heading(c,text=c.title());table.column(c,width=w)
    table.pack(fill='x',pady=15)
    details=tk.Text(work,height=13,bg='#111820',fg='#dce6ef',wrap='word',font=('Consolas',10));details.pack(fill='both',expand=True)
    def action(fn):
        try:fn()
        except Exception as e:messagebox.showerror('Needs attention',str(e))
    def refresh():
        chosen=table.selection();s=Store()
        try:
            items=s.list()
            for row in table.get_children():table.delete(row)
            for t in items:
                scope=t['project']+('/'+t['subproject'] if t['subproject'] else '')
                table.insert('', 'end',iid=t['id'],values=(scope,t['status'],t['goal'][:130]))
            if chosen and table.exists(chosen[0]):table.selection_set(chosen[0])
        finally:s.close()
    def add():
        s=Store()
        try:
            selected='' if subproject.get()=='subproject' else subproject.get()
            s.create(project.get(),goal.get(),selected);goal.delete(0,'end');refresh()
        finally:s.close()
    ttk.Button(bar,text='Add goal',command=lambda:action(add)).pack(side='right')
    def select(_=None):
        if not table.selection():return
        s=Store()
        try:
            details.delete('1.0','end');details.insert('end',json.dumps(s.get(table.selection()[0]),indent=2))
        finally:s.close()
    table.bind('<<TreeviewSelect>>',select)
    controls=ttk.Frame(work);controls.pack(fill='x',pady=10)
    def start():
        (runtime_root()/'PAUSE').unlink(missing_ok=True)
        subprocess.Popen([sys.executable,'-m','assistant.run','run','--hours','8'],cwd=REPO)
    def pause():(runtime_root()/'PAUSE').touch()
    def report():
        s=Store()
        try:p=s.report()
        finally:s.close()
        messagebox.showinfo('Report saved',str(p))
    for label,fn in [('Run up to 8 hours',start),('Pause after current step',pause),('Refresh',refresh),('Morning report',report)]:
        ttk.Button(controls,text=label,command=lambda f=fn:action(f)).pack(side='left',padx=(0,8))
    ttk.Label(work,text='Approved drafts still need implementation and real tests before use.').pack(anchor='w')
    ttk.Label(knowledge,text='Search your private vault. Results stay within the selected project plus shared notes.').pack(anchor='w',pady=10)
    kb=ttk.Frame(knowledge);kb.pack(fill='x');kp=tk.StringVar(value='game')
    ttk.Combobox(kb,textvariable=kp,values=['personal','business','game'],state='readonly',width=12).pack(side='left')
    ks=ttk.Entry(kb,width=14);ks.insert(0,'subproject');ks.pack(side='left',padx=(10,0))
    query=ttk.Entry(kb);query.pack(side='left',fill='x',expand=True,padx=10)
    results=tk.Text(knowledge,bg='#111820',fg='#dce6ef',wrap='word');results.pack(fill='both',expand=True,pady=15)
    def search():
        s=Store()
        try:
            selected='' if ks.get()=='subproject' else ks.get()
            s.index(runtime_root()/'vault');hits=s.search(kp.get(),query.get(),subproject=selected)
            formatted=[]
            for h in hits:
                meta='status='+h['status']+' • producer='+h['producer']
                if h['subproject']:meta+=' • subproject='+h['subproject']
                if h['metadata_errors']:meta+=' • METADATA CONFLICT'
                formatted.append(h['path']+'\n'+meta+'\n'+h['body'])
            results.delete('1.0','end');results.insert('end','\n\n'.join(formatted) or 'No matching notes.')
        finally:s.close()
    ttk.Button(kb,text='Search',command=lambda:action(search)).pack(side='right')
    ttk.Label(knowledge,text='Open the vault folder in Obsidian to edit notes; no paid Sync required.').pack(anchor='w')
    def open_file(p):
        if sys.platform=='win32':os.startfile(str(p))
        else:messagebox.showinfo('Open file',str(p))
    for label,path in [('Edit worker profiles',runtime_root()/'workers.json'),('Edit cloud configuration',runtime_root()/'config.json'),('Open Obsidian vault folder',runtime_root()/'vault'),('Read setup guide',REPO/'docs/assistant/SETUP.md')]:
        ttk.Button(settings,text=label,command=lambda p=path:action(lambda:open_file(p))).pack(anchor='w',pady=8)
    ttk.Label(settings,text='Changes apply on the next run. Cloud-only leadership and free-only routing are mandatory.').pack(anchor='w',pady=20)
    action(refresh);root.mainloop()
if __name__=='__main__':main()
