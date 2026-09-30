import assert from 'node:assert/strict';
import test from 'node:test';
import {baseUrl, jsonBody, graphqlData, hasMetrics, profileOptions} from '../load-testing/contracts.mjs';

test('only bounded loopback origins are allowed', () => {
  for (const value of ['http://127.0.0.1:8000','https://localhost/','http://[::1]:1234']) assert.ok(baseUrl(value));
  for (const value of ['https://example.org','http://localhost.evil','http://admin:secret@localhost','http://127.0.0.1/x','http://localhost?x=1','http://localhost:99999']) assert.throws(() => baseUrl(value));
});
test('malformed JSON is a semantic failure without a thrown exception', () => {
  assert.equal(jsonBody({body:'{'}), null);
  assert.deepEqual(jsonBody({body:'{"status":"ok"}'}), {status:'ok'});
});
test('GraphQL error, partial and unexpected envelopes are rejected', () => {
  for (const body of [null,[],{data:null},{data:[]},{data:{x:1},errors:[{message:'failed'}]},{data:{x:1},errors:{}},{other:1}]) assert.equal(graphqlData(body,'x'),null);
  assert.equal(graphqlData({data:{x:1},errors:[]},'x'),1);
  assert.equal(graphqlData({data:{x:1}},'x'),1);
});
test('metrics require a finite nonnegative sample of the exact family', () => {
  assert.ok(hasMetrics('# TYPE x counter\nx{path="/"} 2\n','x'));
  assert.ok(hasMetrics('x 2e3\n','x'));
  for (const body of ['# HELP x hello\n','xxx 1\n','x nonsense\n','x{a="b"} NaN\n','x -1\n',null]) assert.equal(hasMetrics(body,'x'),false);
});
test('smoke and explicitly selected load profiles keep their budgets', () => {
  assert.equal(profileOptions({ITERATIONS:'10'}).iterations,10);
  assert.equal(profileOptions({}).maxRedirects,0);
  assert.equal(profileOptions({}).thresholds.request_errors[0],'rate==0');
  const load=profileOptions({PROFILE:'load'});
  assert.equal(load.stages.length,4);
  assert.equal(load.thresholds.request_errors[0],'rate<0.05');
  assert.equal(load.stages.reduce((sum,s)=>sum+(s.duration.endsWith('m') ? parseInt(s.duration)*60 : parseInt(s.duration)),0),150);
  for (const env of [{PROFILE:'cloud'},{ITERATIONS:'0'},{ITERATIONS:'2.5'},{ITERATIONS:'100001'}]) assert.throws(()=>profileOptions(env));
});
