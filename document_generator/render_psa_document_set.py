#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, sys
from pathlib import Path
import xml.etree.ElementTree as ET
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

def env_for(path: Path):
    return Environment(loader=FileSystemLoader(str(path.parent)),undefined=StrictUndefined,
        autoescape=select_autoescape(default=True),keep_trailing_newline=True,
        trim_blocks=True,lstrip_blocks=True)

def render(template: Path, values: dict) -> str:
    text=env_for(template).get_template(template.name).render(**values)
    ET.fromstring(text)
    return text

def main():
    p=argparse.ArgumentParser(description='Generate Product_Document and its Document Collection.')
    p.add_argument('document_dir',type=Path)
    p.add_argument('--document-template',required=True,type=Path)
    p.add_argument('--collection-template',required=True,type=Path)
    p.add_argument('--document-lid',required=True); p.add_argument('--collection-lid',required=True)
    p.add_argument('--version-id',default='1.0'); p.add_argument('--title',required=True)
    p.add_argument('--information-model-version',default='1.22.0.0')
    p.add_argument('--publication-year',type=int,required=True); p.add_argument('--publication-date',required=True)
    p.add_argument('--description',required=True); p.add_argument('--modification-date',required=True)
    p.add_argument('--document-modification-description',required=True)
    p.add_argument('--collection-modification-description',required=True)
    p.add_argument('--edition-name',default='1.0'); p.add_argument('--language',default='English')
    p.add_argument('--pdf-file',default='bc_mmo_pwi_data_user_guide.pdf')
    p.add_argument('--document-output',default='bc_mmo_pwi_data_user_guide.xml')
    p.add_argument('--collection-output',default='collection_bc_mmo_pwi_document.xml')
    p.add_argument('--inventory-output',default='collection_bc_mmo_pwi_document.csv')
    a=p.parse_args(); d=a.document_dir.resolve()
    if not d.is_dir(): raise FileNotFoundError(d)
    if not (d/a.pdf_file).is_file(): raise FileNotFoundError(d/a.pdf_file)
    common=dict(version_id=a.version_id, information_model_version=a.information_model_version,
        publication_year=a.publication_year, modification_date=a.modification_date)
    doc_values=dict(common,document_lid=a.document_lid,title=a.title,description=a.description,
        publication_date=a.publication_date,modification_description=a.document_modification_description,
        edition_name=a.edition_name,language=a.language,pdf_file=a.pdf_file)
    doc_text=render(a.document_template.resolve(),doc_values)
    (d/a.document_output).write_text(doc_text,encoding='utf-8',newline='\n')
    inventory=(f'P,{a.document_lid}::{a.version_id}\r\n').encode('utf-8')
    (d/a.inventory_output).write_bytes(inventory)
    coll_values=dict(common,collection_lid=a.collection_lid,
        collection_title='BepiColombo MMO PWI document collection',
        citation_description='This collection contains documentation supporting the BepiColombo Mercury Magnetospheric Orbiter Plasma Wave Investigation archive, including the PWI Data User Guide.',
        modification_description=a.collection_modification_description,
        collection_description='Documentation required to understand and use the BepiColombo MMO PWI data products.',
        inventory_file=a.inventory_output,file_size=len(inventory),
        md5_checksum=hashlib.md5(inventory).hexdigest(),records=1)
    coll_text=render(a.collection_template.resolve(),coll_values)
    (d/a.collection_output).write_text(coll_text,encoding='utf-8',newline='\n')
    print(f'Generated document label: {d/a.document_output}')
    print(f'Generated collection inventory: {d/a.inventory_output}')
    print(f'Generated collection label: {d/a.collection_output}')
if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'ERROR: {e}',file=sys.stderr); raise SystemExit(1)
