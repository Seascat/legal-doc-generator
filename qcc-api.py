"""
企业信息查询 API
启动：python qcc-api.py
查询：http://localhost:5678/api/search?name=华为

通过企查查/搜索引擎获取企业信息
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import urllib.parse

app = Flask(__name__)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

def clean_text(text):
    """清理HTML标签和空白"""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def search_360(name):
    """360搜索 - 适合中文查询"""
    try:
        url = f'https://www.so.com/s?q={urllib.parse.quote(name + " 公司")}'
        resp = requests.get(url, headers=HEADERS, timeout=15)
        
        # 360使用UTF-8
        try:
            html = resp.content.decode('utf-8')
        except:
            html = resp.text
        
        result = {'name': '', 'creditCode': '', 'legalRep': '', 'address': ''}
        
        # 提取搜索结果
        items = re.findall(r'<div class="res-list"[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?<p class="res-rich[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL)
        
        for title, desc in items[:5]:
            full_text = clean_text(title + ' ' + desc)
            
            # 公司名
            if not result['name']:
                n = re.search(r'([^\s,，、]*(?:有限公司|有限责任公司|股份公司|集团|合伙企业)[^\s,，、]*)', full_text)
                if n:
                    result['name'] = n.group(1).strip()
            
            # 信用代码
            c = re.search(r'([0-9A-Za-z]{18})', full_text)
            if c and not result['creditCode']:
                result['creditCode'] = c.group(1).upper()
            
            # 法定代表人
            r = re.search(r'法定代表人[：:]\s*([^\s,，、<&)]{2,8})', full_text)
            if r and not result['legalRep']:
                result['legalRep'] = r.group(1).strip()
        
        # 如果搜狗搜索能拿到名称
        if not result['name']:
            titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
            for t in titles[:3]:
                text = clean_text(t)
                n = re.search(r'([^\s,，、]*(?:有限公司|有限责任公司|股份公司|集团)[^\s,，、]*)', text)
                if n:
                    result['name'] = n.group(1).strip()
                    break
        
        return result
    except Exception as e:
        print(f"  360异常: {e}")
        return {}

@app.route('/api/search', methods=['GET'])
def search():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'error': '请输入公司名称', 'companies': []})
    
    print(f"\n🔍 查询: {name}")
    info = search_360(name)
    companies = []
    
    if info.get('name') or info.get('creditCode'):
        companies.append({
            'name': info.get('name', name),
            'creditCode': info.get('creditCode', ''),
            'legalRep': info.get('legalRep', ''),
            'address': info.get('address', ''),
        })
    
    return jsonify({'source': '360', 'companies': companies})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'note': '企业查询API v2'})

if __name__ == '__main__':
    print("=" * 50)
    print("🏢 企业信息查询 API v2")
    print(f"地址: http://localhost:5678")
    print(f"查询: http://localhost:5678/api/search?name=公司名")
    print(f"按 Ctrl+C 停止")
    print("=" * 50)
    app.run(host='127.0.0.1', port=5678, debug=False)
