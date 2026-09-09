const assert = require('node:assert/strict')
const { test } = require('node:test')
const ts = require('typescript')
const fs = require('node:fs')
require.extensions['.ts'] = (module, filename) => {
  module._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS }
  }).outputText, filename)
}
const { toggleAnswer, isCorrect, recordAnswer, getStats } = require('../src/domain/quiz.ts')

test('多选可选多个并取消，单选与判断始终只有一个选项', () => {
  assert.deepEqual(toggleAnswer(['A'], 'B', 'multiple'), ['A', 'B'])
  assert.deepEqual(toggleAnswer(['A', 'B'], 'A', 'multiple'), ['B'])
  assert.deepEqual(toggleAnswer(['A'], 'B', 'single'), ['B'])
  assert.deepEqual(toggleAnswer(['A'], 'B', 'judge'), ['B'])
})
test('多选必须完全匹配，漏选和多选都判错，顺序不影响答案', () => {
  assert.equal(isCorrect(['B', 'A'], ['A', 'B']), true)
  assert.equal(isCorrect(['A'], ['A', 'B']), false)
  assert.equal(isCorrect(['A', 'B', 'C'], ['A', 'B']), false)
  assert.equal(isCorrect([], ['A']), false)
})
test('重复点击提交只记录一次，空答案不计入记录', () => {
  const record = { question_id: 'q1', selected_answers: ['A'], duration_ms: 1300, is_correct: true }
  const records = recordAnswer([], record)
  assert.equal(recordAnswer(records, record).length, 1)
  assert.equal(recordAnswer([], { ...record, selected_answers: [] }).length, 0)
  assert.equal(records[0].duration_ms, 1300)
})
test('XP 只奖励答对的题目，用时来自本轮记录', () => {
  const records = [
    { question_id: 'q1', selected_answers: ['A'], duration_ms: 1300, is_correct: true },
    { question_id: 'q2', selected_answers: ['B'], duration_ms: 2700, is_correct: false },
  ]
  assert.deepEqual(getStats(records), { xp: 20, correct: 1, durationSeconds: 4 })
  assert.deepEqual(getStats([]), { xp: 0, correct: 0, durationSeconds: 0 })
})
