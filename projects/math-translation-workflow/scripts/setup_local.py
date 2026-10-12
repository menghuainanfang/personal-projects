"""根据当前机器生成翻译工具配置。"""
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'config.json'
if target.exists():
    print(f'保留现有配置：{target}')
    sys.exit(0)
skill=Path.home()/'.agents'/'skills'/'mathtranslations'
cfg={name:shutil.which(name) or name for name in ['latexmk','xelatex','biber','pdftotext','pdftoppm']}
cfg.update(skill=str(skill),python=sys.executable)
target.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
print(f'已生成：{target}')
missing=[name for name in ['latexmk','xelatex','biber','pdftotext','pdftoppm'] if not shutil.which(name)]
if missing:print('请在配置中填写未发现工具的实际路径：'+', '.join(missing))
if not (skill/'SKILL.md').exists():print('尚未发现主技能；按 README 安装完整目录后即可审计。')
