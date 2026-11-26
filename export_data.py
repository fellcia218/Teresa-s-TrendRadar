import sqlite3
import csv
import glob
import os
import json
import time
import sys

# 尝试导入 requests，如果没安装，给出提示
try:
    import requests
except ImportError:
    print("❌ 缺少 requests 库，请检查运行环境。")
    sys.exit(1)

API_KEY = os.environ.get('ZHIPU_API_KEY')

def analyze_sentiment(title):
    """调用 AI 分析单条新闻的情感"""
    if not API_KEY:
        return "neutral", "未配置API_KEY"

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    prompt = f"""
    你是一个资深的舆情分析师。请判断以下新闻事件的真实情感倾向。
    注意：如果新闻表面上是中立的（如通报、回应），或者表面是正面的（如道歉、整改），
    但其根本原因是由前期的负面事件（如事故、违规、侵权）引发的，请务必判定为 negative。
    新闻标题：{title}
    请严格输出以下 JSON 格式，不要输出任何其他废话：
    {{"sentiment": "positive 或 neutral 或 negative", "reason": "一句话解释判定原因"}}
    """
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "glm-4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        # 增强解析容错，防止 AI 返回非标准 JSON
        content = content.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(content)
        return parsed.get('sentiment', 'neutral'), parsed.get('reason', '解析失败')
    except Exception as e:
        print(f"⚠️ 分析【{title}】失败: {e}")
        return "neutral", "AI请求失败"

def export_to_csv():
    db_files = glob.glob('output/news/*.db')
    if not db_files:
        print("没找到数据库文件，跳过导出。")
        return
        
    latest_db = max(db_files, key=os.path.getctime)
    conn = sqlite3.connect(latest_db)
    cursor = conn.cursor()
    
    # 自动寻找新闻表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    target_table = next((t for t in tables if 'news' in t.lower() or 'hot' in t.lower()), tables[0])
            
    cursor.execute(f"SELECT * FROM {target_table} LIMIT 100") # 先限制20条测试
    rows = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    
    # 动态寻找 title 所在的列索引，不再瞎猜 row[1]
    title_idx = column_names.index('title') if 'title' in column_names else 1
    
    new_column_names = column_names + ['sentiment', 'reason']
    
    with open('data.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(new_column_names)
        
        for row in rows:
            title = row[title_idx]
            print(f"🔍 正在分析: {title}")
            sentiment, reason = analyze_sentiment(title)
            
            new_row = list(row) + [sentiment, reason]
            writer.writerow(new_row)
            time.sleep(1) # 延迟1秒，防止被API限流拦截
            
    print(f"✅ 导出成功，共处理 {len(rows)} 条数据。")
    conn.close()

if __name__ == "__main__":
    export_to_csv()
