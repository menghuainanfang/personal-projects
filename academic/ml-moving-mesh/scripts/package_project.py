"""Bundle the source and deliverables, then extract and verify the portable project."""
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    output=ROOT.parent/(ROOT.name+'.zip')
    excluded={'__pycache__','.venv','node_modules','.git','.pytest_cache'}
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(ROOT.rglob('*')):
            relative=path.relative_to(ROOT)
            if (not path.is_file() or excluded.intersection(relative.parts)
                    or path.suffix in {'.pyc','.aux','.log','.out'}
                    or path.name.endswith('_source.snapshot.json')):
                continue
            archive.write(path,Path(ROOT.name)/relative)
    with tempfile.TemporaryDirectory(prefix='ml-mesh-extract-') as tmp:
        with zipfile.ZipFile(output) as archive:
            archive.extractall(tmp)
        unpacked=Path(tmp)/ROOT.name
        subprocess.run([sys.executable,str(unpacked/'scripts/validate_delivery.py')],
                       cwd=unpacked,check=True)
        # Relative links and shared numeric modules must survive the archive.
        assert (unpacked/'paper/paper.pdf').is_file()
        assert (unpacked/'tools/reporting/notes_to_report.py').is_file()
    print(f'{output} ({output.stat().st_size/1024/1024:.2f} MiB); extracted project validation passed.')

if __name__=='__main__':
    main()
