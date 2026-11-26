import sqlite3
import csv
import glob
import os
import json
import requests
import time

# 读取我们刚才在 GitHub Secrets 里存好的钥匙
API_KEY = os.environ.get('ZHIPU_API_KEY')
if not API_KEY:
    print("⚠️ 没有找到 ZHIPU_API_KEY 环境变量，请检查设置！")
    # 为了方便测试，如果没有配置 Secret，这里直接退出
    exit(1)

def analyze_sentiment(title):
    """调用 AI 分析单条新闻的情感，重点识别隐性负面"""
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    
    # 这是给 AI 下达的指令（Prompt），非常关键！
    prompt = f"""
    你是一个资深的舆情分析师。请判断以下新闻事件的真实情感倾向。
    注意：如果新闻表面上是中立的（如通报、回应），或者表面是正面的（如道歉、整改），
    但其根本原因是由前期的负面事件（如事故、违规、侵权）引发的，请务必判定为 negative。
    
    新闻标题：{title}
    
    请严格输出以下 JSON 格式，不要输出任何其他废话：
    {{"sentiment": "positive 或 neutral 或 negative", "reason": "一句话解释判定原因"}}
    """
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "glm-4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # 解析 AI 返回的 JSON，去掉可能存在的 Markdown 符号
        content = content.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(content)
        return parsed['sentiment'], parsed['reason']
    except Exception as e:
        print(f"分析标题【{title}】失败: {e}")
        return "neutral", "AI分析失败"

def export_to_csv():
    db_files = glob.glob('output/news/*.db')
    if not db_files:
        print("没找到数据库文件，跳过导出。")
        return
        
    latest_db = max(db_files, key=os.path.getctime)
    print(f"正在读取最新的数据库: {latest_db}")
    
    conn = sqlite3.connect(latest_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    target_table = tables[0]
    for t in tables:
        if 'news' in t.lower() or 'hot' in t.lower():
            target_table = t
            break
            
    cursor.execute(f"SELECT * FROM {target_table} LIMIT 20") # 为了测试，先只拿20条
    rows = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]
    
    # 我们要给 CSV 增加两个新列
    new_column_names = column_names + ['sentiment', 'reason']
    
    with open('data.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(new_column_names)
        
        for row in rows:
            # 找到标题所在的列（假设第二列是title）
            title = row[1] 
            print(f"正在让 AI 分析: {title}")
            
            # 调用 AI 分析
            sentiment, reason = analyze_sentiment(title)
            
            # 将结果拼接到原数据后面
            new_row = list(row) + [sentiment, reason]
            writer.writerow(new_row)
            
            # 稍微停顿一下，防止调用太快被智谱限流
            time.sleep(0.5) 
            
    print(f"✅ 成功！已将 {len(rows)} 条数据导出并分析了情感。")
    conn.close()

if __name__ == "__main__":
    export_to_csv()
