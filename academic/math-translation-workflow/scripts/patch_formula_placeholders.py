"""保持批量翻译前后每个公式占位符的出现次数。"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / 'tools/pdf2zh/pdf2zh/site-packages/babeldoc/format/pdf/document_il/midend/il_translator_llm_only.py'
source = path.read_text(encoding='utf-8')
anchor = '                    output_unicode = translated_text\n'
check = '''
                    placeholder_pattern = r"\\{v\\d+\\}"
                    if Counter(re.findall(placeholder_pattern, input_unicode)) != Counter(
                        re.findall(placeholder_pattern, output_unicode)
                    ):
                        raise ValueError("Formula placeholder counts changed")
'''
if 'Formula placeholder counts changed' not in source:
    if source.count(anchor) != 1:
        raise RuntimeError('当前 BabelDOC 版本的翻译入口与补丁不匹配。')
    source = source.replace('import json\n', 'import json\nfrom collections import Counter\n', 1)
    source = source.replace(anchor, anchor + check, 1)
    path.write_text(source, encoding='utf-8')
print('公式占位符校验已启用。')
