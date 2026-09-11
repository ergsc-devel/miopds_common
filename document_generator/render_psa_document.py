#!/usr/bin/env python3
import argparse, sys
from pathlib import Path
import xml.etree.ElementTree as ET
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
p=argparse.ArgumentParser()
p.add_argument('document_dir',type=Path); p.add_argument('--template',required=True,type=Path)
p.add_argument('--document-lid',required=True); p.add_argument('--document-vid',default='1.0'); p.add_argument('--title',required=True)
p.add_argument('--information-model-version',default='1.22.0.0'); p.add_argument('--publication-year',required=True,type=int)
p.add_argument('--description',required=True); p.add_argument('--modification-date',required=True); p.add_argument('--modification-description',required=True)
p.add_argument('--document-name',required=True); p.add_argument('--publication-date',required=True); p.add_argument('--edition-name',default='1.0'); p.add_argument('--language',default='English')
p.add_argument('--file',action='append',required=True); p.add_argument('--output',default='bc_mmo_pwi_data_user_guide.xml')
a=p.parse_args(); d=a.document_dir.resolve(); t=a.template.resolve()
try:
    if not d.is_dir(): raise FileNotFoundError(d)
    fs=[]
    for v in a.file:
        name,std=v.rsplit(':',1)
        if Path(name).name != name or not (d/name).is_file(): raise FileNotFoundError(d/name)
        fs.append({'file_name':name,'document_standard_id':std})
    env=Environment(loader=FileSystemLoader(str(t.parent)),undefined=StrictUndefined,autoescape=select_autoescape(default=True),keep_trailing_newline=True)
    s=env.get_template(t.name).render(document_lid=a.document_lid,document_vid=a.document_vid,title=a.title,information_model_version=a.information_model_version,publication_year=a.publication_year,description=a.description,modification_date=a.modification_date,modification_description=a.modification_description,document_name=a.document_name,publication_date=a.publication_date,edition_name=a.edition_name,language=a.language,document_files=fs)
    ET.fromstring(s); (d/a.output).write_text(s,encoding='utf-8',newline='\n'); print(f'Generated: {d/a.output}')
except Exception as e:
    print(f'ERROR: {e}',file=sys.stderr); raise SystemExit(1)
