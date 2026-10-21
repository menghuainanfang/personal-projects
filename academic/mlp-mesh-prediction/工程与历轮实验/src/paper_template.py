import re

def text_tex(text):
    def escape(s):
        s=s.replace('\\',r'\textbackslash{}')
        for a,b in [('&',r'\&'),('%',r'\%'),('#',r'\#'),('_',r'\_')]: s=s.replace(a,b)
        return s.replace('→',r'$\to$')
    # Inline math is copied unchanged; prose escapes TeX-special characters.
    parts=re.split(r'(\$[^$]+\$)',text)
    out=''.join(p if p.startswith('$') else escape(p) for p in parts)
    out=re.sub(r'\*\*(.+?)\*\*',r'\\textbf{\1}',out)
    out=re.sub(r'`([^`]+)`',lambda m:r'\texttt{'+m[1]+'}',out)
    out=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',lambda m:r'\href{'+m[2]+'}{'+m[1]+'}',out)
    return out

def to_tex(markdown):
    header=r'''\documentclass[UTF8,a4paper,zihao=5,fontset=fandol]{ctexart}
\usepackage[margin=21mm,top=19mm,bottom=19mm]{geometry}
\usepackage{amsmath,amssymb,graphicx,booktabs,array,caption,xcolor,adjustbox}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small 机器学习课程设计}\fancyhead[R]{\small 二维变分自适应网格预测}
\fancyfoot[C]{\thepage}\setlength{\headheight}{15pt}
\setlength{\parskip}{3pt}\linespread{1.12}
\ctexset{section={format=\large\bfseries,beforeskip=8pt,afterskip=4pt},subsection={format=\normalsize\bfseries,beforeskip=6pt,afterskip=3pt}}
\captionsetup{font=small,labelformat=empty,hypcap=false,skip=3pt}
\setlength{\emergencystretch}{1em}
\begin{document}
'''
    lines=markdown.splitlines(); result=[header]; i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line: result.append('\n');i+=1;continue
        if line=='<!-- pagebreak -->': result.append(r'\newpage'+'\n');i+=1;continue
        if line=='$$':
            j=i+1
            while lines[j].strip()!='$$':j+=1
            result.append('\\[\n'+'\n'.join(lines[i+1:j])+'\n\\]\n');i=j+1;continue
        if line.startswith('# '):
            result.append(r'\begin{center}{\LARGE\bfseries '+text_tex(line[2:])+r'}\end{center}'+'\n');i+=1;continue
        if line.startswith('## '):result.append(r'\section*{'+text_tex(line[3:])+'}\n');i+=1;continue
        if line.startswith('### '):result.append(r'\subsection*{'+text_tex(line[4:])+'}\n');i+=1;continue
        if line.startswith('!['):
            m=re.match(r'!\[(.*?)\]\((.*?)\)',line)
            result.append(r'\begin{center}\includegraphics[width=\linewidth]{'+m[2]+r'}\captionof{figure}{'+text_tex(m[1])+r'}\end{center}'+'\n');i+=1;continue
        if line.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                if not re.match(r'^\|[\s:|\-]+\|$',lines[i].strip()):
                    block.append([s.strip() for s in lines[i].strip().strip('|').split('|')])
                i+=1
            wide=len(block[0])>=5
            start=(r'\begin{center}\small\resizebox{\linewidth}{!}{' if wide else
                   r'\begin{center}\small\begin{adjustbox}{max width=\linewidth}')
            result.append(start+r'\begin{tabular}{'+'l'*len(block[0])+r'}\toprule'+'\n')
            for j,row in enumerate(block):
                result.append(' & '.join(text_tex(c) for c in row)+r' \\'+'\n')
                if j==0:result.append(r'\midrule'+'\n')
            result.append(r'\bottomrule\end{tabular}'+('}' if wide else r'\end{adjustbox}')+r'\end{center}'+'\n');continue
        if re.match(r'^\[\d+\] ',line):
            result.append(r'\begin{sloppypar}'+text_tex(line)+r'\end{sloppypar}'+'\n\n')
        else:
            result.append(text_tex(line)+'\n\n')
        i+=1
    result.append(r'\end{document}')
    return ''.join(result)

