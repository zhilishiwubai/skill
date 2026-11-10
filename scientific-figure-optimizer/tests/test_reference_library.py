"""Self-contained local fixtures; no private data, network, or native applications."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('reference_library',ROOT/'scripts/reference_library.py')
lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)


class ReferenceLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'cards').mkdir()
        self.save('library.json',{'schema_version':1,'roots':{'local':str(self.root)}})
        self.sources={}
        for i in [1,2,3]:
            source=self.root/f'work{i}.txt';source.write_text(f'Original teaching source {i}')
            self.sources[f'S{i}']={'sha256':lib.sha(source),'locator':{'root':'local','relative_path':source.name}}
            (self.root/f'preview{i}.png').write_bytes(f'distinct preview bytes {i}'.encode())
            self.save(f'cards/C{i}.json',self.card(i))
        self.save('sources.json',self.sources)
        self.save('research-evidence.json',[{'resource_id':'E1','resource_role':'RESEARCH_EVIDENCE','sha256':self.sources['S1']['sha256'],'locator':{'root':'local','relative_path':'work1.txt'},'mapping_status':'UNMAPPED'}])
        self.assertEqual(lib.check(self.root,True,True)['status'],'PASS')

    def save(self,name,obj):
        lib.write_json(self.root/name,obj)

    def get(self,name):return lib.read_json(self.root/name)

    def card(self,i):
        return {'case_id':f'C{i}','source_id':f'S{i}','figure_number':'6',
          'resource_role':'VISUAL_REFERENCE','category':'curves','title':'Response comparison',
          'scientific_question':'Compare load displacement curves without changing units',
          'tags':['force','displacement'],'source_sha256':self.sources[f'S{i}']['sha256'],
          'preview':f'preview{i}.png','preview_sha256':lib.sha(self.root/f'preview{i}.png'),
          'visual_review':{'status':'REVIEWED','preview_sha256':lib.sha(self.root/f'preview{i}.png'),'reviewer':'fixture author','method':'Synthetic fixture declaration, not a real visual review'},
          'editability':{'level':'IMAGE_REFERENCE','reopened_verified':False},
          'mapping':{'status':'NOT_APPLICABLE_REFERENCE_ONLY'},
          'rights':{'status':'SELF_AUTHORED','publication_authorized':False},
          'layout':{'order':'left to right'},'visual_encoding':{'lines':'solid versus dashed'},
          'borrow_rules':[{'rule_id':'R1','text':'Distinguish series using line styles and units'}],
          'avoid':'Do not fabricate results','applicable_to':['load displacement comparison']}

    def request(self):
        return {'scientific_problem':'load displacement curves','function':'curves',
          'target_reader':'students','figure_type':'line plot','size_mm':[120,85],
          'editing_requirement':'SVG text and paths','main_claim':'Teaching example only',
          'data_sources':['self-authored synthetic data'],
          'design':{k:'explicit choice' for k in ['layout','encoding','font','colors','annotations','output_formats']},
          'new_design':'Own data and visual arrangement',
          'adoptions':[{'case_id':f'C{i}','viewed_preview_sha256':lib.sha(self.root/f'preview{i}.png'),
           'visual_observations':'Self-authored fixture observation for exercising validation only',
           'rule_ids':['R1'],'applied_to':'Use line style and unit labels'} for i in [1,2]]}

    def rejected(self):
        try:result=lib.check(self.root,True)
        except lib.Invalid:return
        self.assertEqual(result['status'],'FAIL')

    def test_full_hash_and_incremental_index(self):
        r=lib.check(self.root,False,True)
        self.assertEqual(r['files_hashed'],0);self.assertEqual(r['cached_hashes_reused'],6)
        self.assertEqual(lib.check(self.root,True)['files_hashed'],6)

    def test_semantic_search_ignores_filename(self):
        r=lib.search(self.root,'荷载位移对比','curves')
        self.assertEqual(len(r['candidates']),3)
        self.assertTrue(all('Scientific expression function: curves' in c['reasons'] for c in r['candidates']))
        self.assertEqual(lib.search(self.root,'astronomy')['candidates'],[])

    def test_stop_words_and_substrings_do_not_pad_irrelevant_cases(self):
        c=self.get('cards/C3.json');c.update(category='workflow',title='Research pipeline',
          scientific_question='Search and screen records',tags=['workflow'],
          layout={'order':'first and second stage'},
          borrow_rules=[{'rule_id':'R1','text':'Keep stage labels and arrows'}],
          applicable_to=['Literature search'])
        self.save('cards/C3.json',c);lib.check(self.root,True,True)
        result=lib.search(self.root,'Compare load displacement curves using redundant line style and marker encoding','curves')
        self.assertEqual({r['case_id'] for r in result['candidates']},{'C1','C2'})
        self.assertIsNotNone(result['limitation'])

    def test_duplicate_figure_panels_do_not_count_twice(self):
        c=self.get('cards/C2.json');c.update(source_id='S1',figure_number='06b',source_sha256=self.sources['S1']['sha256'])
        self.save('cards/C2.json',c);self.rejected()
        c['duplicate_of']='C1';self.save('cards/C2.json',c)
        r=lib.check(self.root,True,True);self.assertEqual(r['status'],'PASS');self.assertEqual(r['unique_figures'],2)

    def test_invalid_duplicate_target(self):
        c=self.get('cards/C2.json');c['duplicate_of']='missing';self.save('cards/C2.json',c);self.rejected()

    def test_duplicate_preview_bytes(self):
        c=self.get('cards/C2.json');c['preview']='preview1.png';c['preview_sha256']=lib.sha(self.root/c['preview'])
        c['visual_review']['preview_sha256']=c['preview_sha256'];self.save('cards/C2.json',c);self.rejected()

    def test_card_id_filename_mismatch(self):
        c=self.get('cards/C1.json');c['case_id']='C2';self.save('cards/C1.json',c)
        with self.assertRaises(lib.Invalid):lib.check(self.root)

    def test_missing_source_and_changed_preview(self):
        (self.root/'work1.txt').rename(self.root/'moved.txt');self.rejected()
        (self.root/'moved.txt').rename(self.root/'work1.txt')
        (self.root/'preview1.png').write_bytes(b'changed');self.rejected()
        with self.assertRaises(lib.Invalid):lib.read_case(self.root,'C1')

    def test_unreviewed_not_adopted(self):
        c=self.get('cards/C1.json');c['visual_review']['status']='UNREVIEWED';self.save('cards/C1.json',c)
        with self.assertRaisesRegex(lib.Invalid,'stale'):lib.search(self.root,'load displacement')
        lib.check(self.root,True,True)
        self.assertNotIn('C1',[r['case_id'] for r in lib.search(self.root,'load displacement')['candidates']])
        with self.assertRaises(lib.Invalid):lib.make_brief(self.root,self.request(),self.root/'output')
        self.assertFalse((self.root/'output').exists())

    def test_native_reopen_claim_needs_project_and_proof(self):
        c=self.get('cards/C1.json');c['editability']={'level':'NATIVE_REOPEN_VERIFIED','reopened_verified':True}
        self.save('cards/C1.json',c);self.rejected()

    def test_data_available_claim_needs_real_data_file(self):
        c=self.get('cards/C1.json');c['editability']={'level':'DATA_AVAILABLE','data_available':True}
        self.save('cards/C1.json',c);self.rejected()

    def test_wrong_root_json_and_observation_types_are_controlled(self):
        with self.assertRaisesRegex(lib.Invalid,'JSON object'):lib.make_brief(self.root,[],self.root/'bad')
        r=self.request();r['adoptions'][0]['visual_observations']=['not text']
        with self.assertRaisesRegex(lib.Invalid,'text observations'):lib.make_brief(self.root,r,self.root/'bad')
        self.save('library.json',[])
        with self.assertRaisesRegex(lib.Invalid,'configuration'):lib.check(self.root)

    def test_unmapped_evidence_not_promoted(self):
        r=self.request();r['research_evidence_used']=[{'resource_id':'E1','as_specimen_evidence':True}]
        with self.assertRaisesRegex(lib.Invalid,'UNMAPPED'):lib.make_brief(self.root,r,self.root/'bad')
        self.assertFalse((self.root/'bad').exists())
        e=self.get('research-evidence.json');e[0]['specimen_id']='A1';self.save('research-evidence.json',e);self.rejected()

    def test_two_source_trace_and_original_schema_sidecar(self):
        request=self.request();request['renderer_brief']={'version':1,'input':'source.csv'}
        result=lib.make_brief(self.root,request,self.root/'task')
        self.assertEqual(result['source_works'],2)
        events=self.get('task/retrieval-and-use.json')
        self.assertEqual(sum(e['event']=='RULES_ADOPTED' for e in events),2)
        self.assertEqual(self.get('task/plot-brief.json'),request['renderer_brief'])
        self.assertFalse(self.get('task/figure-brief.json')['model_training'])
        with self.assertRaisesRegex(lib.Invalid,'already exists'):lib.make_brief(self.root,request,self.root/'task')

    def test_missing_second_source_requires_explicit_limitation(self):
        r=self.request();r['adoptions']=r['adoptions'][:1]
        with self.assertRaises(lib.Invalid):lib.make_brief(self.root,r,self.root/'limited')
        r['limited_sources_reason']='Only one relevant reviewed source exists'
        self.assertEqual(lib.make_brief(self.root,r,self.root/'limited')['status'],'LIMITED_REFERENCE_PLAN')

    def test_wrong_visual_hash_unknown_rule_and_invalid_size(self):
        for mode in ['hash','rule','size']:
            with self.subTest(mode=mode):
                r=self.request()
                if mode=='hash':r['adoptions'][0]['viewed_preview_sha256']='wrong'
                if mode=='rule':r['adoptions'][0]['rule_ids']=['invented']
                if mode=='size':r['size_mm']=[float('inf'),-1]
                with self.assertRaises(lib.Invalid):lib.make_brief(self.root,r,self.root/'bad')
                self.assertFalse((self.root/'bad').exists())

    def test_write_failure_leaves_no_success_folder(self):
        with patch.object(lib,'write_json',side_effect=OSError('simulated disk failure')):
            with self.assertRaises(OSError):lib.make_brief(self.root,self.request(),self.root/'failed')
        self.assertFalse((self.root/'failed').exists())
        self.assertEqual(list(self.root.glob('.sfo-brief-*')),[])

    def test_paths_and_bad_json_cli_exit(self):
        with self.assertRaises(lib.Invalid):lib.inside(self.root,'../escape')
        self.save('library.json',{'schema_version':1,'roots':{},'cards':'../outside'})
        r=subprocess.run([sys.executable,str(ROOT/'scripts/reference_library.py'),'--library',str(self.root),'index'],capture_output=True,text=True)
        self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stderr)['status'],'FAIL')
        (self.root/'library.json').write_text('{"schema_version":1,')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/reference_library.py'),'--library',str(self.root),'index'],capture_output=True,text=True)
        self.assertEqual(r.returncode,2);self.assertFalse((self.root/'output').exists())

    def test_corrupt_or_edited_index_blocks_search(self):
        original=(self.root/'index.json').read_bytes()
        for contents in ['{','[]','{"schema_version":1}']:
            with self.subTest(contents=contents):
                (self.root/'index.json').write_text(contents)
                with self.assertRaises(lib.Invalid):lib.search(self.root,'load displacement')
        (self.root/'index.json').write_bytes(original)
        index=self.get('index.json');index['cases'][0]['title']='Edited';self.save('index.json',index)
        with self.assertRaisesRegex(lib.Invalid,'stale'):lib.search(self.root,'load displacement')

    def test_missing_index_cannot_pass_validation(self):
        (self.root/'index.json').unlink()
        with self.assertRaisesRegex(lib.Invalid,'Build and validate'):lib.check(self.root,True)
        self.assertEqual(lib.check(self.root,True,True)['status'],'PASS')

    def test_stale_card_change_requires_explicit_reindex(self):
        c=self.get('cards/C1.json');c['borrow_rules'][0]['text']='Changed expression rule'
        self.save('cards/C1.json',c)
        with self.assertRaisesRegex(lib.Invalid,'stale'):lib.search(self.root,'load displacement')
        lib.check(self.root,True,True)
        self.assertEqual(len(lib.search(self.root,'load displacement')['candidates']),3)

    def test_changed_preview_or_source_is_not_returned_as_reviewed(self):
        for filename in ['preview1.png','work1.txt']:
            with self.subTest(filename=filename):
                p=self.root/filename;original=p.read_bytes();stat=p.stat()
                p.write_bytes(b'X'*len(original))
                import os
                os.utime(p,ns=(stat.st_atime_ns,stat.st_mtime_ns))
                with self.assertRaisesRegex(lib.Invalid,'integrity errors'):lib.search(self.root,'load displacement')
                p.write_bytes(original);os.utime(p,ns=(stat.st_atime_ns,stat.st_mtime_ns))

    def test_wrong_nested_card_types_fail_without_traceback(self):
        original=self.get('cards/C1.json')
        for field in ['visual_review','rights','mapping','editability','layout','visual_encoding']:
            with self.subTest(field=field):
                c=copy.deepcopy(original);c[field]=[];self.save('cards/C1.json',c)
                r=subprocess.run([sys.executable,str(ROOT/'scripts/reference_library.py'),'--library',str(self.root),'validate','--deep'],capture_output=True,text=True)
                self.assertEqual(r.returncode,2);self.assertNotIn('Traceback',r.stderr)
                self.assertIn(field,json.loads(r.stderr)['error'])
        self.save('cards/C1.json',original)

    def test_wrong_cache_and_evidence_types_are_controlled(self):
        self.save('index-cache.json',[])
        with self.assertRaisesRegex(lib.Invalid,'index-cache'):lib.check(self.root,True)
        lib.check(self.root,True,True) # full rebuild repairs only generated cache/index
        self.save('research-evidence.json',[1])
        with self.assertRaisesRegex(lib.Invalid,'evidence objects'):lib.check(self.root,True,True)

    def test_missing_scientific_question_is_not_validated(self):
        c=self.get('cards/C1.json');del c['scientific_question'];self.save('cards/C1.json',c)
        with self.assertRaisesRegex(lib.Invalid,'scientific_question'):lib.check(self.root,True,True)


if __name__=='__main__':unittest.main()
