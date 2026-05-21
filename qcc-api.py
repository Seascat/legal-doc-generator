"""
企业信息查询 API v6 - 稳定版
启动：python qcc-api.py
查询：http://localhost:5680/api/search?name=华为

功能：
  - 搜索公司名称（360搜索，稳定）
  - 使用预置查询精确匹配企查查数据
  - 搜索结果显示 名称、信用代码、法人
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import json
import os

app = Flask(__name__)
CORS(app)

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# 预置公司查询（通过企查查MCP已验证的精确数据）
# 格式：{关键词: [{name, creditCode, legalRep, address}]}
PRESET_DB = {}

def load_presets():
    """加载预置公司数据"""
    preset_path = os.path.join(os.path.dirname(__file__), 'qcc-presets.json')
    if os.path.exists(preset_path):
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_preset(keyword, companies):
    """保存查询结果到预置库"""
    preset_path = os.path.join(os.path.dirname(__file__), 'qcc-presets.json')
    db = PRESET_DB
    if keyword not in db:
        db[keyword] = companies
    try:
        with open(preset_path, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except:
        pass

def search_360(name):
    """360搜索企业名称"""
    try:
        url = f'https://www.so.com/s?q={urllib.parse.quote(name + " 公司")}'
        resp = requests.get(url, headers={'User-Agent': UA}, timeout=10)
        soup = BeautifulSoup(resp.text, 'lxml')
        
        companies = []
        seen = set()
        
        for h3 in soup.find_all('h3'):
            text = h3.get_text(strip=True)
            # 只匹配含"有限公司"等的名称
            n = re.search(r'([\u4e00-\u9fff]{2,}(?:有限公司|有限责任公司|股份公司|集团有限公司|合伙企业|股份有限))', text)
            if n:
                cn = n.group(1).strip()
                # 过滤无效结果
                if cn.startswith('关于') or cn.startswith('其他人'):
                    continue
                if cn not in seen and (name[:2] in cn or any(kw in cn for kw in name.split())):
                    seen.add(cn)
                    companies.append({'name': cn, 'creditCode': '', 'legalRep': '', 'address': ''})
        
        return companies
    except Exception as e:
        print(f"  360异常: {e}")
        return []

@app.route('/api/search', methods=['GET'])
def search():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'error': '请输入公司名称', 'companies': []})
    
    print(f"\n🔍 查询: '{name}'")
    
    # 1. 先查预置数据库
    global PRESET_DB
    if not PRESET_DB:
        PRESET_DB = load_presets()
    
    if name in PRESET_DB:
        print(f"  ✅ 命中预置库: {len(PRESET_DB[name])} 条")
        return jsonify({'source': 'preset', 'companies': PRESET_DB[name]})
    
    # 2. 360搜索
    companies = search_360(name)
    
    if companies:
        print(f"  ✅ 360搜索: {len(companies)} 条")
        for c in companies[:3]:
            print(f"     {c['name']}")
    else:
        print("  ❌ 未找到")
        return jsonify({'source': '', 'companies': []})
    
    return jsonify({'source': '360', 'companies': companies[:5]})

@app.route('/api/update', methods=['POST'])
def update():
    """手动添加/更新公司数据（由WorkBuddy助手调用）"""
    data = request.get_json()
    if not data or 'key' not in data or 'companies' not in data:
        return jsonify({'error': '需要key和companies参数'}), 400
    
    global PRESET_DB
    PRESET_DB[data['key']] = data['companies']
    save_preset(data['key'], data['companies'])
    return jsonify({'status': 'ok', 'count': len(data['companies'])})

@app.route('/api/presets', methods=['GET'])
def list_presets():
    """列出已保存的公司"""
    global PRESET_DB
    if not PRESET_DB:
        PRESET_DB = load_presets()
    keys = list(PRESET_DB.keys())
    return jsonify({'count': len(keys), 'keys': keys})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'version': 6})

if __name__ == '__main__':
    PRESET_DB = load_presets()
    print("=" * 50)
    print("🏢 企业信息查询 API v6")
    print(f"端口: 5681")
    print(f"预置公司: {len(PRESET_DB)} 条")
    print(f"查询: http://localhost:5681/api/search?name=华为")
    print(f"更新: POST /api/update (由助手自动调用)")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5681, debug=False)
