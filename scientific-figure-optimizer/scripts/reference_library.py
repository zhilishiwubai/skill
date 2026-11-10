"""Local-only scientific references: semantic tags, traceable reading and rule adoption."""
from __future__ import annotations
import argparse
from collections import Counter
import html
import json
import math
import os
from pathlib import Path
import re
import sys
import shutil
import tempfile

from figure import Invalid, read_json, require, sha, write_json

VERSION='1.1'
STOP_WORDS={'and','the','for','with','using','from','into','that','this','these','those',
            'are','was','were','has','have','not','only','use','our','your','its',
            'can','will','would','should','than','then','but','without','through'}
ALIASES={
 'structure':['结构','装配','剖面','零件','structure','assembly','cross section'],
 'mechanism':['机理','机制','阶段','缓冲','耗能','mechanism','stage','dissipation'],
 'apparatus':['装置','加载','试验台','试验设备','apparatus','loading','test rig'],
 'curves':['曲线','荷载','位移','应变','加载功','对比','curve','load','displacement','strain'],
 'fe_model':['有限元','网格','边界','仿真','fe model','mesh','boundary'],
 'workflow':['流程','技术路线','检索','筛选','复现','workflow','flowchart','pipeline'],
 'multipanel':['多面板','多指标','对照','multipanel','comparison']}


def inside(root, rel):
    require(isinstance(rel,str) and rel, 'Missing library relative path')
    p=(root/rel).resolve()
    require(p.is_relative_to(root.resolve()), 'Library path escapes its root')
    return p


def load_library(path):
    require(path, 'Supply --library or SFO_REFERENCE_LIBRARY; no private folders are searched automatically')
    root=Path(path).resolve();config=read_json(root/'library.json')
    require(isinstance(config,dict) and config.get('schema_version')==1 and isinstance(config.get('roots'),dict), 'Invalid library configuration: expected schema_version=1 object with roots')
    require(all(isinstance(v,str) and v.strip() for v in config['roots'].values()),'library.json roots must map aliases to nonempty directory strings')
    sources=read_json(inside(root,config.get('source_file','sources.json')))
    require(isinstance(sources,dict) and all(isinstance(s,dict) for s in sources.values()),'sources.json must map source IDs to source objects')
    cards=[]
    for p in sorted(inside(root,config.get('cards','cards')).glob('*.json')):
        c=read_json(p)
        require(isinstance(c,dict) and c.get('case_id')==p.stem,'Case ID must match its card filename: '+p.name)
        for key in ['visual_review','editability','rights','mapping','visual_encoding','layout']:
            require(isinstance(c.get(key),dict),f'{p.name}.{key} must be an object')
        for key in ['source_id','title','scientific_question','avoid']:
            require(isinstance(c.get(key),str) and c[key].strip(),f'{p.name}.{key} must be nonempty text')
        require(c.get('category') in ALIASES,f'{p.name}.category is not a supported scientific function')
        for key in ['tags','applicable_to']:
            require(isinstance(c.get(key),list) and all(isinstance(t,str) and t.strip() for t in c[key]),f'{p.name}.{key} must be an array of text')
        rules=c.get('borrow_rules')
        require(isinstance(rules,list) and all(isinstance(r,dict) and isinstance(r.get('rule_id'),str) and r['rule_id'].strip() and isinstance(r.get('text'),str) and r['text'].strip() for r in rules),f'{p.name}.borrow_rules must contain rule_id/text objects')
        require(len({r['rule_id'] for r in rules})==len(rules),f'{p.name}.borrow_rules contains duplicate rule_id')
        cards.append(c)
    require(cards, 'Library contains no case cards')
    return root,config,sources,cards


def source_path(config, source):
    loc=source.get('locator',{})
    require(isinstance(loc,dict),'Source locator must be an object')
    require(loc.get('root') in config['roots'], 'Unknown source-root alias')
    root=Path(config['roots'][loc['root']]).expanduser().resolve()
    return inside(root,loc.get('relative_path'))


def canonical_number(number):
    parts=re.findall(r'\d+',str(number))
    require(parts, 'Missing figure number')
    return '.'.join(str(int(n)) for n in parts)


def metadata_snapshot(root, config):
    paths=[root/'library.json',inside(root,config.get('source_file','sources.json'))]
    paths+=sorted(inside(root,config.get('cards','cards')).glob('*.json'))
    if (root/'research-evidence.json').exists():paths.append(root/'research-evidence.json')
    return {p.relative_to(root).as_posix():sha(p) for p in paths}


def index_matches(root,config,cards):
    path=root/'index.json'
    require(path.is_file(),'Build and validate the index before searching: index --deep')
    index=read_json(path)
    require(isinstance(index,dict) and index.get('schema_version')==2,'Index schema is old or invalid; rebuild with index --deep')
    require(isinstance(index.get('cases'),list) and all(isinstance(c,dict) for c in index['cases']),'Index cases must be an array of objects; rebuild with index --deep')
    expected=[{k:c[k] for k in ['case_id','source_id','category','title','tags']}|{'visual_review':c['visual_review']['status']} for c in cards if not c.get('duplicate_of')]
    require(index['cases']==expected and index.get('metadata_sha256')==metadata_snapshot(root,config),'Index is stale or edited; rebuild with index --deep after reviewing changes')
    require(isinstance(index.get('validation'),dict) and index['validation'].get('status')=='PASS','Index has no passing validation record')


def check(path, deep=False, update_index=False):
    root,config,sources,cards=load_library(path)
    errors=[];warnings=[];ids=set();canonical=set();previews={};count=Counter()
    cache_path=root/'index-cache.json'
    if update_index and deep:
        cache={}  # Explicit full rebuild can recover a corrupt derived cache/index.
    else:
        cache=read_json(cache_path) if cache_path.exists() else {}
        require(isinstance(cache,dict) and all(isinstance(v,dict) and type(v.get('size')) is int and type(v.get('mtime_ns')) is int and isinstance(v.get('sha256'),str) and re.fullmatch('[0-9a-f]{64}',v['sha256']) for v in cache.values()),'index-cache.json must map paths to size/mtime_ns/sha256 records; rebuild with index --deep')
    if not update_index:index_matches(root,config,cards)
    current={};reused=0;hashed=0
    def fingerprint(p):
        nonlocal reused,hashed
        key=str(p.resolve())
        if key in current:return current[key]['sha256']
        stat=p.stat();old=cache.get(key,{})
        if not deep and old.get('size')==stat.st_size and old.get('mtime_ns')==stat.st_mtime_ns:
            digest=old['sha256'];reused+=1
        else:digest=sha(p);hashed+=1
        current[key]={'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,'sha256':digest}
        return digest
    for c in cards:
        label=c.get('case_id','UNKNOWN')
        try:
            require(re.fullmatch(r'[A-Za-z0-9_-]+',label) and label not in ids, 'Duplicate or unsafe case_id');ids.add(label)
            require(c.get('resource_role')=='VISUAL_REFERENCE','Reference cards cannot silently include research evidence')
            sid=c['source_id'];require(sid in sources,'Missing source identity')
            key=(sid,canonical_number(c['figure_number']))
            if c.get('duplicate_of'):
                require(c['duplicate_of'] in {x['case_id'] for x in cards} and c['duplicate_of']!=label,'Duplicate alias target missing or self-referential')
                target=next(x for x in cards if x['case_id']==c['duplicate_of'])
                require(not target.get('duplicate_of') and (target['source_id'],canonical_number(target['figure_number']))==key,'Duplicate alias must refer to the same independent figure')
                warnings.append(label+': duplicate alias excluded from count');continue
            require(key not in canonical,'Duplicate source work/figure, including split panels');canonical.add(key);count[sid]+=1
            require(c['source_sha256']==sources[sid]['sha256'],'Card/source hash disagreement')
            src=source_path(config,sources[sid]);require(src.is_file(),'Source file missing: '+str(src))
            require(fingerprint(src)==c['source_sha256'],'Source hash changed')
            preview=inside(root,c['preview']);require(preview.is_file(),'Preview missing')
            digest=fingerprint(preview);require(digest==c['preview_sha256'],'Preview hash changed')
            require(digest not in previews,'Duplicate preview bytes: '+str(previews.get(digest)));previews[digest]=label
            review=c.get('visual_review',{})
            if review.get('status')=='REVIEWED':
                require(review.get('preview_sha256')==digest and review.get('reviewer') and review.get('method'),'Visual review not bound to this preview')
            else:warnings.append(label+': NOT_VISUALLY_REVIEWED; cannot supply adopted rules')
            edit=c.get('editability',{})
            require(edit.get('level') in ['IMAGE_REFERENCE','DATA_AVAILABLE','NATIVE_PROJECT_PRESENT','NATIVE_REOPEN_VERIFIED'],'Unknown editability level')
            require(edit['level']!='DATA_AVAILABLE' or edit.get('data_available') is True,'Data availability has not been established')
            if edit['level']=='DATA_AVAILABLE':
                data=edit.get('data_file')
                require(data and edit.get('data_sha256'),'Data availability needs a file and hash')
                data=inside(root,data);require(data.is_file() and fingerprint(data)==edit['data_sha256'],'Redraw data missing or changed')
            if edit['level'] in ['NATIVE_PROJECT_PRESENT','NATIVE_REOPEN_VERIFIED']:
                require(edit.get('native_project') and edit.get('native_project_sha256'),'Native project presence needs a path and hash')
                project=inside(root,edit['native_project']);require(project.is_file() and fingerprint(project)==edit['native_project_sha256'],'Native project missing or changed')
            require(edit['level']!='NATIVE_REOPEN_VERIFIED' or edit.get('reopened_verified') is True,'Native project was not reopened/verified')
            if edit.get('reopened_verified'):
                require(edit['level']=='NATIVE_REOPEN_VERIFIED','Reopened flag contradicts editability level')
                proof=c['editability'].get('validation_record')
                require(proof,'Native editability claimed without evidence')
                r=read_json(inside(root,proof));require(r.get('status')=='PASS' and r.get('project_sha256')==edit.get('native_project_sha256') and edit.get('native_project_sha256'),'Invalid native reopen evidence')
            require(c.get('mapping',{}).get('status')=='NOT_APPLICABLE_REFERENCE_ONLY','Reference must not become mapped specimen evidence')
            rights=c.get('rights',{})
            require(rights.get('publication_authorized') is False or (rights.get('publication_authorized') is True and rights.get('authorization_record') and inside(root,rights['authorization_record']).is_file()),'Publication authority needs an existing record; this is not legal approval')
            require(c.get('borrow_rules') and c.get('avoid') and c.get('visual_encoding'),'Case card lacks expression rules or limits')
        except (Invalid,KeyError,OSError,TypeError) as e:errors.append(label+': '+str(e))
    for sid,n in count.items():
        if n>3:errors.append(sid+': exceeds 3 independent figures per source work')
    evidence_path=root/'research-evidence.json';evidence=read_json(evidence_path) if evidence_path.exists() else []
    require(isinstance(evidence,list) and all(isinstance(e,dict) for e in evidence),'research-evidence.json must be an array of evidence objects')
    missing_evidence=[];evidence_hashes={}
    for e in evidence:
        try:
            require(e.get('resource_role')=='RESEARCH_EVIDENCE','Research register needs its own evidence role')
            p=source_path(config,{'locator':e['locator']})
            if not p.is_file():missing_evidence.append(e['resource_id'])
            else:
                digest=fingerprint(p)
                require(e.get('sha256')==digest,'Research source hash missing or changed')
                evidence_hashes.setdefault(digest,[]).append(e['resource_id'])
            if e.get('mapping_status')=='UNMAPPED':
                require(not e.get('specimen_id') and not e.get('data_file'),'UNMAPPED evidence contains asserted mapping')
        except (Invalid,KeyError,OSError) as error:errors.append(e.get('resource_id','UNKNOWN')+': '+str(error))
    if missing_evidence:errors.append('Research source paths missing: '+','.join(missing_evidence))
    result={'status':'PASS' if not errors else 'FAIL','unique_figures':len(canonical),'source_works':len(count),'per_source':dict(count),'visually_reviewed':sum(c.get('visual_review',{}).get('status')=='REVIEWED' and not c.get('duplicate_of') for c in cards),'research_evidence':len(evidence),'unmapped_evidence':sum(e.get('mapping_status')=='UNMAPPED' for e in evidence),'duplicate_research_groups':[v for v in evidence_hashes.values() if len(v)>1],'errors':errors,'warnings':warnings,'hash_mode':'FULL_REHASH' if deep else 'SIZE_MTIME_INCREMENTAL_NOT_TAMPER_PROOF','files_hashed':hashed,'cached_hashes_reused':reused}
    if update_index:
        require(not errors,'Index not updated: '+'; '.join(errors))
        write_json(root/'index.json',{'schema_version':2,'metadata_sha256':metadata_snapshot(root,config),'cases':[{'case_id':c['case_id'],'source_id':c['source_id'],'category':c['category'],'title':c['title'],'tags':c['tags'],'visual_review':c['visual_review']['status']} for c in cards if not c.get('duplicate_of')],'validation':result})
        write_json(cache_path,current)
    return result


def search(path, query, function=None, limit=5, include_unreviewed=False):
    root,config,sources,cards=load_library(path)
    require(isinstance(query,str) and query.strip(),'Query must be nonempty text')
    require(3<=limit<=5,'Return 3–5 candidates when enough relevant cases exist')
    index_matches(root,config,cards)
    validation=check(path,deep=True)
    require(validation['status']=='PASS','Search blocked by library integrity errors: '+'; '.join(validation['errors']))
    q=query.casefold();functions={k for k,words in ALIASES.items() if any(w in q for w in words)}
    if function:require(function in ALIASES,'Unknown scientific function');functions.add(function)
    tokens=set(re.findall(r'\b[a-z][a-z_-]{2,}\b',q))-STOP_WORDS;results=[]
    for c in cards:
        if c.get('duplicate_of') or c.get('resource_role')!='VISUAL_REFERENCE':continue
        reviewed=c.get('visual_review',{}).get('status')=='REVIEWED'
        if not reviewed and not include_unreviewed:continue
        text=json.dumps([c['title'],c['scientific_question'],c['tags'],c['layout'],c['borrow_rules'],c['applicable_to']],ensure_ascii=False).casefold()
        reasons=[];score=0
        if c['category'] in functions:score+=10;reasons.append('Scientific expression function: '+c['category'])
        for k in functions:
            matched=[w for w in ALIASES[k] if w in q and w in text]
            if matched:score+=min(6,len(matched)*2);reasons.append('Task concepts: '+', '.join(matched))
        words=set(re.findall(r'\b[a-z][a-z_-]{2,}\b',text))
        matched=sorted(tokens & words)
        score+=len(matched)
        if matched:reasons.append('Task vocabulary: '+', '.join(matched))
        if score:results.append({'case_id':c['case_id'],'source_id':c['source_id'],'title':c['title'],'score':score,'reasons':reasons,'visual_review':c['visual_review']['status'],'card':f"cards/{c['case_id']}.json",'preview':c['preview'],'preview_sha256':c['preview_sha256'],'rights':c['rights']['status'],'editability':c['editability']['level']})
    results.sort(key=lambda r:(-r['score'],r['case_id']))
    # Prefer source diversity without importing unrelated zero-score cases.
    chosen=[];counts=Counter()
    for r in results:
        if counts[r['source_id']]<2:chosen.append(r);counts[r['source_id']]+=1
        if len(chosen)==limit:break
    if len(chosen)<limit:
        chosen += [r for r in results if r not in chosen][:limit-len(chosen)]
    return {'query':query,'scientific_functions':sorted(functions),'candidates':chosen,'limitation':None if len(chosen)>=3 else 'Fewer than 3 relevant candidates; do not pad with unrelated images','ranking_fields':'scientific function, concepts, question, rules, applicability; not filename'}


def read_case(path, case_id):
    root,_,_,cards=load_library(path)
    require(re.fullmatch(r'[A-Za-z0-9_-]+',case_id),'Unsafe case_id')
    c=next((c for c in cards if c['case_id']==case_id),None);require(c is not None,'Unknown case_id')
    preview=inside(root,c['preview']);require(sha(preview)==c['preview_sha256'],'Preview changed')
    return {'card':c,'card_sha256':sha(root/'cards'/f'{case_id}.json'),'preview_path':str(preview),'preview_sha256':sha(preview),'notice':'Reading image bytes/path is not visual inspection. Open the preview in the authorized viewer and record task-specific observations.'}


def make_brief(path, request, output):
    root,config,sources,cards=load_library(path);byid={c['case_id']:c for c in cards}
    require(isinstance(request,dict),'Figure Brief request must be a JSON object')
    for key in ['scientific_problem','target_reader','figure_type','size_mm','editing_requirement','main_claim','data_sources','design','new_design','adoptions']:
        require(key in request and request[key], 'Missing Figure Brief field: '+key)
    require(isinstance(request['design'],dict) and isinstance(request['adoptions'],list) and isinstance(request['data_sources'],list),'Design must be an object; adoptions and data_sources must be arrays')
    for key in ['scientific_problem','target_reader','figure_type','editing_requirement','main_claim','new_design']:
        require(isinstance(request[key],str) and request[key].strip(),key+' must be nonempty text')
    require(isinstance(request['size_mm'],list),'size_mm must be a two-number array')
    require(len(request['size_mm'])==2 and all(type(v) in [int,float] and math.isfinite(v) and v>0 for v in request['size_mm']),'Invalid figure size')
    for key in ['layout','encoding','font','colors','annotations','output_formats']:
        require(request['design'].get(key),'Missing design choice: '+key)
    result=search(path,request['scientific_problem'],request.get('function'))
    candidates={c['case_id'] for c in result['candidates']};selected=[];events=[{'event':'SEARCH','result':result}]
    for adopted in request['adoptions']:
        require(isinstance(adopted,dict),'Each adoption must be an object')
        cid=adopted['case_id'];require(cid in candidates,'Selected case must occur in this task search results')
        require(cid not in [s['case_id'] for s in selected],'Duplicate adoption case')
        c=byid[cid];r=read_case(path,cid)
        require(c['visual_review']['status']=='REVIEWED','Unreviewed case cannot supply learned rules')
        observation=adopted.get('visual_observations','')
        require(isinstance(observation,str) and adopted.get('viewed_preview_sha256')==r['preview_sha256'] and len(observation.strip())>=12,'Task-specific actual viewing attestation and text observations required')
        valid={rule['rule_id']:rule['text'] for rule in c['borrow_rules']}
        require(adopted.get('rule_ids') and all(i in valid for i in adopted['rule_ids']),'Unknown or missing adopted rule')
        require(adopted.get('applied_to'),'Explain how rule changes this task design')
        selected.append(adopted|{'source_id':c['source_id'],'card_sha256':r['card_sha256'],'adopted_rules':{i:valid[i] for i in adopted['rule_ids']},'rights':c['rights'],'source_mapping':c['mapping']})
        events.extend([{'event':'CASE_CARD_READ','case_id':cid,'sha256':r['card_sha256']},{'event':'PREVIEW_BYTES_READ','case_id':cid,'sha256':r['preview_sha256']},{'event':'VISUAL_REVIEW_DECLARED','case_id':cid,'observations':adopted['visual_observations'],'sha256':r['preview_sha256'],'limit':'Auditable declaration, not independent machine proof of perception'},{'event':'RULES_ADOPTED','case_id':cid,'rules':adopted['rule_ids'],'applied_to':adopted['applied_to']}])
    diversity=len({c['source_id'] for c in selected})
    require(diversity>=2 or request.get('limited_sources_reason'),'Need two source works, or an explicit limitation reason')
    for used in request.get('research_evidence_used',[]):
        e=next((e for e in read_json(root/'research-evidence.json') if e['resource_id']==used['resource_id']),None)
        require(e is not None,'Unknown research evidence')
        require(not used.get('as_specimen_evidence') or e['mapping_status']=='MAPPED_VERIFIED','UNMAPPED photo cannot become confirmed specimen evidence')
    plan=request|{'status':'PLAN_VALIDATED_NOT_SCIENTIFICALLY_APPROVED' if diversity>=2 else 'LIMITED_REFERENCE_PLAN','candidates':result['candidates'],'adoptions':selected,'sources_used':diversity,'model_training':False,'human_scientific_review':'PENDING','events':events}
    output=Path(output).resolve();require(not output.exists(),'Output already exists; use a new task folder')
    output.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.sfo-brief-',dir=output.parent)).resolve()
    try:
        write_json(staging/'figure-brief.json',plan);write_json(staging/'retrieval-and-use.json',events)
        if request.get('renderer_brief'):
            # Preserve the strict original v1 CSV brief schema in a separate file.
            write_json(staging/'plot-brief.json',request['renderer_brief'])
        staging.rename(output)
    except BaseException:
        require(staging.parent==output.parent and staging.name.startswith('.sfo-brief-'),'Unsafe staging cleanup')
        shutil.rmtree(staging)
        raise
    return {'status':plan['status'],'selected_case_ids':[c['case_id'] for c in selected],'source_works':diversity,'output':str(output)}


def gallery(path):
    from PIL import Image,ImageDraw
    root,_,_,cards=load_library(path);tiles=[];parts=['<!doctype html><meta charset="utf-8"><title>Local references</title><style>body{font-family:sans-serif;margin:30px;background:#eee}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}article{background:white;padding:16px}img{max-width:100%;height:240px;object-fit:contain}</style><h1>本地科学图形参考库</h1><p>仅本地参考，不是模型训练；查看不等于复制发表授权。研究证据另存，不混入参考案例计数。</p><div class="grid">']
    for c in cards:
        if c.get('duplicate_of'):continue
        preview=inside(root,c['preview']);im=Image.open(preview).convert('RGB');im.thumbnail((460,305));tile=Image.new('RGB',(480,350),'white');tile.paste(im,((480-im.width)//2,28+(305-im.height)//2));ImageDraw.Draw(tile).text((10,8),c['case_id']+' / '+c['category'],fill='black');tiles.append(tile)
        parts.append(f'<article><a href="{html.escape(c["preview"],quote=True)}"><img src="{html.escape(c["preview"],quote=True)}"></a><h3>{html.escape(c["case_id"]+" "+c["title"])}</h3><p>{html.escape(c["source"]["authors"])} {c["source"]["year"]} · 图{html.escape(c["figure_number"])} · PDF第{c["page_1based"]}页</p><p>{html.escape(c["borrow_rules"][0]["text"])}</p><p>限制：{html.escape(c["avoid"])}</p><a href="cards/{c["case_id"]}.json">案例卡</a> · <a href="{c["page_preview"]}">原页预览</a></article>')
    for i in range(0,len(tiles),4):
        sheet=Image.new('RGB',(960,700),'#dddddd')
        for j,t in enumerate(tiles[i:i+4]):sheet.paste(t,((j%2)*480,(j//2)*350))
        sheet.save(root/f'overview-{i//4+1:02d}.jpg',quality=93)
    (root/'index.html').write_text(''.join(parts)+'</div>',encoding='utf-8')
    return {'status':'GENERATED_LOCAL_DERIVATIVE_PREVIEWS','cases':len(tiles),'gallery':str(root/'index.html')}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--library',default=os.environ.get('SFO_REFERENCE_LIBRARY'))
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['index','validate']:
        q=sub.add_parser(name);q.add_argument('--deep',action='store_true')
    q=sub.add_parser('search');q.add_argument('--query',required=True);q.add_argument('--function',choices=ALIASES);q.add_argument('--limit',type=int,default=5);q.add_argument('--include-unreviewed',action='store_true')
    sub.add_parser('read').add_argument('case_id')
    q=sub.add_parser('brief');q.add_argument('request');q.add_argument('--out',required=True)
    sub.add_parser('gallery')
    args=p.parse_args()
    try:
        if args.command in ['index','validate']:r=check(args.library,args.deep,args.command=='index')
        elif args.command=='search':r=search(args.library,args.query,args.function,args.limit,args.include_unreviewed)
        elif args.command=='read':r=read_case(args.library,args.case_id)
        elif args.command=='brief':r=make_brief(args.library,read_json(args.request),args.out)
        else:r=gallery(args.library)
        print(json.dumps(r,ensure_ascii=True));return 2 if r.get('status')=='FAIL' else 0
    except (Invalid,OSError,KeyError,TypeError,ValueError) as error:
        print(json.dumps({'status':'FAIL','error':str(error)},ensure_ascii=True),file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
