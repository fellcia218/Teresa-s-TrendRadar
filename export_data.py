import sqlite3
import csv
import glob
import os

def export_to_csv():
    # 找到 output/news 文件夹下所有的 .db 数据库文件
    db_files = glob.glob('output/news/*.db')
    
    if not db_files:
        print("没找到数据库文件，跳过导出。")
        return
        
    # 取最新生成的那个数据库文件
    latest_db = max(db_files, key=os.path.getctime)
    print(f"正在读取最新的数据库: {latest_db}")
    
    conn = sqlite3.connect(latest_db)
    cursor = conn.cursor()
    
    # 查一下数据库里有什么表，并找到存放新闻的那个表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    target_table = None
    for t in tables:
        # 通常新闻表会叫 news 或者 hotlist
        if 'news' in t.lower() or 'hot' in t.lower():
            target_table = t
            break
            
    if not target_table:
        target_table = tables[0] # 如果没找到，默认拿第一个表
        
    print(f"准备导出表: {target_table}")
    
    # 读取数据
    cursor.execute(f"SELECT * FROM {target_table} LIMIT 100")
    rows = cursor.fetchall()
    
    # 获取列名（表头）
    column_names = [description[0] for description in cursor.description]
    
    # 写入 data.csv
    with open('data.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(column_names)
        writer.writerows(rows)
        
    print(f"✅ 成功！已将 {len(rows)} 条数据导出到 data.csv")
    conn.close()

if __name__ == "__main__":
    export_to_csv()
