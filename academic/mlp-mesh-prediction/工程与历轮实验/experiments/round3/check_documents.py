"""Check the compiled article and render pages for visual review."""
from pathlib import Path
import re,json
import pymupdf
from PIL import Image,ImageOps,ImageDraw
ROOT=Path(__file__).resolve().parent

def main():
    pdf=pymupdf.open(ROOT/'paper/report.pdf')
    assert 5<=len(pdf)<=8, f'Article has {len(pdf)} pages'
    log=(ROOT/'paper/report.log').read_text(encoding='utf-8',errors='replace')
    problems=[line for line in log.splitlines() if any(s in line for s in ['Overfull','Missing character','Undefined control sequence'])]
    if problems:raise ValueError('\n'.join(problems))
    out=ROOT/'results/pdf_preview';out.mkdir(exist_ok=True)
    thumbs=[]
    for i,page in enumerate(pdf):
        assert len(page.get_text())>80
        pix=page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
        path=out/f'page_{i+1}.png';pix.save(path)
        im=Image.open(path).convert('RGB');im.thumbnail((520,735))
        frame=Image.new('RGB',(540,770),'#d9dee4');frame.paste(im,((540-im.width)//2,20))
        ImageDraw.Draw(frame).text((20,750),f'Page {i+1}',fill='black')
        thumbs.append(frame)
    sheet=Image.new('RGB',(540*2,770*((len(thumbs)+1)//2)),'#d9dee4')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%2)*540,(i//2)*770))
    sheet.save(out/'contact.png')
    result=dict(pdf_pages=len(pdf),tex_layout_warnings=problems,page_text_lengths=[len(p.get_text()) for p in pdf],
                html_build_checks='existing reporting generator verifier',
                browser_visual_check='Not completed: local file protocol is unavailable in the browser tool')
    (ROOT/'results/document_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(result)

if __name__=='__main__':main()
