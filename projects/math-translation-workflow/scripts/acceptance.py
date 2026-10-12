"""验证源文保留、构建恢复、资源错误及样例结构；不调用翻译 API。"""
import json,re,shutil,subprocess,sys
from collections import Counter
from pathlib import Path
from workflow import ROOT,build,init,extract
import pymupdf

sample=ROOT/'samples'/'Linear algebra sample'
results=[]
def record(name,passed,detail):
    results.append({'check':name,'passed':bool(passed),'detail':detail})
    if not passed:raise AssertionError(name)
en=(sample/'source'/'main.tex').read_text(encoding='utf8')
zh=(sample/'translation'/'main.tex').read_text(encoding='utf8')
math=r'\$[^$]+\$|\\begin\{align\*?\}(.*?)\\end\{align\*?\}'
def chunks(text):return [m.group(0) for m in re.finditer(math,text,re.S)]
record('样例数学块内容及出现次数一致',Counter(chunks(en))==Counter(chunks(zh)),'中文语序可以变化；不适用于任意宏展开后的数学等价判定')
display=r'\\begin\{align\*?\}.*?\\end\{align\*?\}'
record('行间公式顺序一致',re.findall(display,en,re.S)==re.findall(display,zh,re.S),'逐个比对公式块与顺序')
for command in ['label','ref','eqref','cite','includegraphics']:
    pattern=rf'\\{command}(?:\[[^]]*\])?\{{([^}}]+)\}}'
    record(command+' 顺序一致',re.findall(pattern,en)==re.findall(pattern,zh),'含目标与顺序')
record('物理页覆盖 1-4',re.findall(r'SOURCE_PDF_PAGE: (\d+)',zh)==['1','2','3','4'],'每页一处，连续无重复')
for name in ['original.pdf','translated-zh.pdf']:
    doc=pymupdf.open(ROOT/'output'/'pdf'/name)
    record(name+' 页数',len(doc)==4,'4 页')
    links=[l for page in doc for l in page.get_links()]
    record(name+' 内部链接',any(l.get('page',-1)>=0 and l['kind'] in [pymupdf.LINK_GOTO,pymupdf.LINK_NAMED] for l in links),'PDF 中实际存在可解析的内部目标')
    text='\n'.join(p.get_text() for p in doc)
    (ROOT/'evidence'/f'{name}.txt').write_text(text,encoding='utf8')
    record(name+' 引用已解析','??' not in text,'公式 (1)-(3)，定义 1.1，定理 2.1，习题 3.1，图 1；详见提取文本')
target=ROOT/'output'/'acceptance'/'project with spaces'
if target.exists():target=target.with_name(target.name+' '+str(len(list(target.parent.iterdir()))))
init(sample/'source',target)
source_before=(sample/'source'/'main.tex').read_bytes()
old=(ROOT/'output'/'pdf'/'translated-zh.pdf').read_bytes()
bad=target/'translation';(bad/'main.tex').write_text(r'\documentclass{article}\begin{document}\undefinedLocalCommand\end{document}',encoding='utf8')
try:build(bad)
except RuntimeError:record('编译失败明确退出',True,'故意使用未定义命令，保留 compile.log')
else:record('编译失败明确退出',False,'未捕获')
(bad/'main.tex').write_text(r'\documentclass{article}\usepackage{graphicx}\begin{document}\includegraphics{absent-figure}\end{document}',encoding='utf8')
audit=subprocess.run([sys.executable,str(ROOT/'vendor'/'mathtranslations-skill'/'scripts'/'audit_latex.py'),str(bad),'--strict'],capture_output=True,text=True)
(ROOT/'evidence'/'missing-resource-audit.txt').write_text(audit.stdout+audit.stderr,encoding='utf8')
record('缺失插图静态审计',audit.returncode!=0,'报告 absent-figure')
try:build(bad)
except RuntimeError:record('缺失插图编译失败',True,'图文件缺失时失败，不生成最终 result.pdf')
else:record('缺失插图编译失败',False,'未捕获')
record('失败未覆盖已完成成果',old==(ROOT/'output'/'pdf'/'translated-zh.pdf').read_bytes(),'直接比较字节')
record('原始源文件未修改',source_before==(sample/'source'/'main.tex').read_bytes(),'直接比较字节')
shutil.copytree(sample/'translation',bad,dirs_exist_ok=True)
recovered=build(bad)
record('修复后可继续构建',(recovered/'result.pdf').exists(),'带空格路径，独立构建目录')
extract(ROOT/'output'/'pdf'/'original.pdf',target/'extracted',1,4)
before=(target/'extracted'/'page-0001.txt').read_bytes()
extract(ROOT/'output'/'pdf'/'original.pdf',target/'extracted',1,4)
record('重复提取保留已完成页',before==(target/'extracted'/'page-0001.txt').read_bytes(),'已有页面跳过，失败页可重跑')
(ROOT/'evidence'/'acceptance.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
print(f'{len(results)} 项通过')
