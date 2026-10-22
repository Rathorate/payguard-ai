import test from 'node:test';
import assert from 'node:assert/strict';
import {questionPanel,renderConversation} from '../public/static/questions-ui.js';

test('case Q&A escapes questions, answers and source excerpts without executable markup',()=>{
  const attack='<img src=x onerror=alert(1)>';
  const output=renderConversation([{role:'user',content:attack},{role:'assistant',source:'GROQ',report:{findings:[
    {category:'RECORDED',statement:attack,sources:[{evidence_id:'e1',quote:attack}]}]}}],[{id:'e1',title:attack}]);
  assert.ok(!output.includes('<img'));
  assert.ok(output.includes('&lt;img'));
  assert.ok(output.includes('data-evidence-ref="e1"'));
  assert.ok(questionPanel().includes('Answers cannot edit, approve or submit'));
});
