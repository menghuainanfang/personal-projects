"""通过新启动的 Codex app-server 验证技能目录；不发起模型请求。"""
import json, subprocess, threading, queue, time, shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=subprocess.Popen([shutil.which('codex'),'app-server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf8',errors='replace',bufsize=1)
q=queue.Queue()
def reader():
    for line in p.stdout: q.put(line)
threading.Thread(target=reader,daemon=True).start()
records=[]
def rpc(i,method,params):
    p.stdin.write(json.dumps({'id':i,'method':method,'params':params})+'\n');p.stdin.flush()
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        try: line=q.get(timeout=1)
        except queue.Empty: continue
        msg=json.loads(line);records.append(msg)
        if msg.get('id')==i:return msg
    raise TimeoutError(method)
try:
    print(rpc(1,'initialize',{'clientInfo':{'name':'translation-audit','version':'1.0'},'capabilities':{'experimentalApi':True}}).get('error','initialized'))
    p.stdin.write('{"method":"initialized"}\n');p.stdin.flush()
    response=rpc(2,'skills/list',{'cwds':[str(root)],'forceReload':True})
    (root/'evidence'/'skill-discovery.json').write_text(json.dumps(response,ensure_ascii=False,indent=2),encoding='utf8')
    for entry in response.get('result',{}).get('data',[]):
        for skill in entry.get('skills',[]):
            if 'mathtranslations' in skill.get('name',''): print(skill)
    if 'error' in response: print(response['error'])
finally:
    p.terminate();p.wait(timeout=10)
