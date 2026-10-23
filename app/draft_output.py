"""Validate structured merchant paragraphs and render declared source references."""
import json
import re
from .providers import ProviderError


def draft_schema(records):
    paragraph = {'type': 'object', 'additionalProperties': False,
                 'required': ['text', 'evidence_ids'], 'properties': {
                     'text': {'type': 'string'}, 'evidence_ids': {'type': 'array',
                         'items': {'type': 'string', 'enum': [e.id for e in records]}}}}
    return {'type': 'object', 'additionalProperties': False,
            'required': ['paragraphs', 'missing_facts'], 'properties': {
                'paragraphs': {'type': 'array', 'items': paragraph},
                'missing_facts': {'type': 'array', 'items': {'type': 'string'}}}}


def render_draft(raw, records):
    known = {e.id for e in records}
    try:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate key')
                result[key] = value
            return result
        data = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(data, dict) or set(data) != {'paragraphs', 'missing_facts'}:
            raise ValueError('Invalid draft shape')
        paragraphs, gaps = data['paragraphs'], data['missing_facts']
        if not isinstance(paragraphs, list) or not 1 <= len(paragraphs) <= 4:
            raise ValueError('Invalid paragraphs')
        if not isinstance(gaps, list) or len(gaps) > 3:
            raise ValueError('Invalid gaps')
        output = []
        for paragraph in paragraphs:
            if not isinstance(paragraph, dict) or set(paragraph) != {'text', 'evidence_ids'}:
                raise ValueError('Invalid paragraph')
            text, identities = paragraph['text'], paragraph['evidence_ids']
            if not isinstance(text, str) or not 20 <= len(text.strip()) <= 1600 or '[' in text or ']' in text:
                raise ValueError('Invalid text')
            if not isinstance(identities, list) or not 1 <= len(identities) <= 4:
                raise ValueError('Missing source')
            if any(not isinstance(identity, str) or identity not in known for identity in identities):
                raise ValueError('Unknown source')
            if len(set(identities)) != len(identities):
                raise ValueError('Duplicate source')
            output.append(text.strip()+' '+ ' '.join('['+identity+']' for identity in identities))
        for gap in gaps:
            if not isinstance(gap, str) or not 5 <= len(gap.strip()) <= 400 or '[' in gap or ']' in gap:
                raise ValueError('Invalid gap')
            # Reject known unnecessary whereabouts requests. This narrow guard is
            # not a semantic/privacy classifier; mandatory review remains necessary.
            whereabouts = (
                r"\b(?:buyer|customer|recipient)(?:['’]s|s)?\s+(?:(?:physical|real[- ]time)\s+)?(?:whereabouts|presence|location|geolocation|gps)\b",
                r"\b(?:buyer|customer|recipient)\b.{0,30}\b(?:being|present)\b.{0,40}\b(?:delivery|address|home)\b",
                r"\b(?:whereabouts|geolocation|gps coordinates)\b.{0,35}\b(?:buyer|customer|recipient)\b")
            if any(re.search(pattern, gap, re.IGNORECASE) for pattern in whereabouts):
                raise ProviderError('AI draft requested unnecessary buyer whereabouts; no draft was changed. Review existing merchant records instead.')
        if gaps:
            output.append('Evidence gaps:\n'+'\n'.join('- '+gap.strip() for gap in gaps))
        rendered = '\n\n'.join(output)
        if len(rendered) > 6000:
            raise ValueError('Oversized response')
        return rendered
    except (ValueError, TypeError, KeyError) as exc:
        raise ProviderError('AI draft has invalid paragraphs or source IDs; no draft was changed. Review the evidence manually or retry later.') from exc
