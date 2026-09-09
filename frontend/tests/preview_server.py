"""仅供 UI 验收：静态 H5 + 固定 HTTP 响应，不调用模型。"""
import json
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTION = {
    'id': 'q1', 'type': 'single', 'stem': 'RAG 与传统搜索最核心的区别是什么？',
    'options': [
        {'key': 'A', 'text': '只负责找到网页链接'},
        {'key': 'B', 'text': '检索资料后，让模型结合资料生成回答'},
        {'key': 'C', 'text': '完全不需要任何外部信息'},
        {'key': 'D', 'text': '只能用于图片搜索'},
    ],
    'answer': ['B'], 'explanation': '传统搜索把资料交给你；RAG 先检索相关资料，再把资料作为上下文交给大模型，由模型组织成回答。',
    'knowledge_point': '易错点', 'difficulty': 'easy',
}
QUESTIONS = [dict(QUESTION, id=f'q{i + 1}') for i in range(5)]
QUESTIONS[2] = dict(QUESTION, id='q3', type='multiple', stem='RAG 的哪些环节会影响回答质量？（多选）', answer=['A', 'B'], options=[{'key':'A','text':'检索结果的相关性'},{'key':'B','text':'知识库资料的质量'},{'key':'C','text':'用户手机的壁纸'},{'key':'D','text':'选项按钮的颜色'}])
QUESTIONS[3] = dict(QUESTION, id='q4', type='judge', stem='RAG 仍然需要维护和更新知识库。', answer=['A'], options=[{'key':'A','text':'正确'},{'key':'B','text':'错误'}])
QUESTIONS[4] = dict(QUESTION, id='q5', stem='企业知识库包含多个版本的制度文档，如果检索同时返回过期条款和最新条款，应该怎样组织提供给模型的上下文，才能避免生成的回答混淆适用范围？', options=[{'key':'A','text':'不加区分地拼接全部条款，让模型自行猜测哪些制度仍然有效。'},{'key':'B','text':'标记文档版本、发布日期和适用范围，优先提供当前有效且相关的条款，并在回答中保留依据。'},{'key':'C','text':'只看文件标题是否有关键词，忽略正文内容。'},{'key':'D','text':'完全不检索，凭模型记忆回答企业内部制度问题。'}])

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.end_headers()
    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        time.sleep(2)
        if self.path.endswith('/quiz/generate'):
            result = {'quiz_id': 'visual-test', 'title': 'RAG 入门闯关', 'summary': 'UI 验收固定题库', 'questions': QUESTIONS}
        else:
            records = data['answer_records']
            correct = sum(sorted(r['selected_answers']) == sorted(q['answer']) for r, q in zip(records, QUESTIONS))
            result = {'accuracy': round(correct / 5 * 100), 'mastered_points': ['RAG 基本结构', '检索与生成关系'], 'weak_points': ['向量检索', '知识库更新机制'], 'three_line_summary': ['先检索，再生成；', '资料决定回答边界；', '知识库质量影响最终效果。'], 'advice': ['再练习一次。']}
        body = json.dumps({'code':0,'message':'ok','data':result}, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers()
        self.wfile.write(body)

if __name__ == '__main__':
    print('UI preview: http://127.0.0.1:8766', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8766), partial(Handler, directory=str(ROOT / 'dist-h5'))).serve_forever()
