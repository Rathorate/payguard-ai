"""Immutable passage references shared by analysis and case questions.

Only server-owned catalog entries can become source excerpts. Resolution is not
factual verification: each caller still validates its task-specific report.
"""
import json


def source_catalog(records):
    passages=[]
    for record in records:
        for start in range(0,len(record.content),700):
            quote=record.content[start:start+700]
            if len(quote.strip())>=5:
                passages.append({'ref':'S'+str(len(passages)+1),'evidence_id':record.id,
                                 'title':record.title,'quote':quote})
    return passages



def source_schema(passages):
    finding={'type':'object','additionalProperties':False,'required':['category','statement','source_refs'],
        'properties':{'category':{'type':'string','enum':['RECORDED','MISSING','CONFLICT']},
            'statement':{'type':'string'},'source_refs':{'type':'array','items':{
                'type':'string','enum':[p['ref'] for p in passages]}}}}
    return {'type':'object','additionalProperties':False,'required':['findings'],
            'properties':{'findings':{'type':'array','items':finding}}}



def resolve_sources(raw, passages, *, max_findings=12):
    known={p['ref']:p for p in passages}
    try:
        def unique(pairs):
            result={}
            for key,value in pairs:
                if key in result:raise ValueError('Duplicate key')
                result[key]=value
            return result
        data=json.loads(raw,object_pairs_hook=unique)
        if not isinstance(data,dict) or set(data)!={'findings'} or not isinstance(data['findings'],list) or not 1<=len(data['findings'])<=max_findings:
            raise ValueError('Invalid answer')
        findings=[]
        for finding in data['findings']:
            if not isinstance(finding,dict) or set(finding)!={'category','statement','source_refs'}:
                raise ValueError('Invalid finding')
            refs=finding['source_refs']
            if not isinstance(refs,list) or len(refs)>4 or any(not isinstance(ref,str) or ref not in known for ref in refs):
                raise ValueError('Invalid source reference')
            if len(set(refs))!=len(refs):raise ValueError('Duplicate source reference')
            findings.append({'category':finding['category'],'statement':finding['statement'],
                'sources':[{'evidence_id':known[ref]['evidence_id'],'quote':known[ref]['quote']} for ref in refs]})
    except (ValueError,KeyError,TypeError) as exc:
        raise ValueError('Invalid source-reference response') from exc
    return {'findings':findings}


