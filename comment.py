import os
import requests
import json
from datetime import datetime
import time

#这个程序会遍历所有的程序再开始保存

# 全局配置
COOKIE = "_uuid="
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Cookie": COOKIE
}
SAVE_PATH = "C:\Base1\srt"

# 动态类型映射表
DYNAMIC_TYPE_MAP = {
    "DYNAMIC_TYPE_DRAW": 11,
    "DYNAMIC_TYPE_WORD": 17,
    "DYNAMIC_TYPE_FORWARD": 17
}

def get_all_dynamics(mid):
    """获取用户全部动态（分页版）"""
    all_dynamics = []
    offset = ""
    has_more = True
    retry_count = 3
    
    while has_more:
        url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
        params = {
            "host_mid": mid,
            "offset": offset,
            "offset_dynamic_id": 0
        }
        
        for _ in range(retry_count):
            try:
                response = requests.get(url, headers=HEADERS, params=params, timeout=10)
                response.raise_for_status()
                data = json.loads(response.text)
                
                if data["code"] != 0:
                    print(f"API返回错误: {data['message']}")
                    return []
                
                # 处理动态数据
                for item in data["data"]["items"]:
                    dynamic_type = DYNAMIC_TYPE_MAP.get(item["type"], 17)
                    
                    # 提取真实oid
                    if dynamic_type == 11:
                        oid = item["modules"]["module_dynamic"]["major"]["draw"]["id"]
                    else:
                        oid = item["id_str"]
                    
                    timestamp = item["modules"]["module_author"]["pub_ts"]
                    pub_date = datetime.fromtimestamp(timestamp)
                    
                    all_dynamics.append({
                        "oid": oid,
                        "pub_date": pub_date,
                        "type": dynamic_type
                    })
                
                # 更新分页参数
                has_more = data["data"]["has_more"]
                offset = data["data"]["offset"]
                time.sleep(1)  # 添加请求间隔
                break
                
            except Exception as e:
                print(f"请求失败: {str(e)}，剩余重试次数：{retry_count-1}")
                time.sleep(3)
                if _ == retry_count-1:
                    has_more = False
                continue
                
    return all_dynamics

def get_all_replies(oid, dynamic_type):
    """获取全部评论（包含子评论）"""
    all_images = []
    next_page = 0
    retry_count = 3
    
    while True:
        url = "https://api.bilibili.com/x/v2/reply/main"
        params = {
            "type": dynamic_type,
            "oid": oid,
            "mode": 3,
            "next": next_page
        }
        
        for _ in range(retry_count):
            try:
                response = requests.get(url, headers=HEADERS, params=params, timeout=10)
                response.raise_for_status()
                data = json.loads(response.text)
                
                if data["code"] != 0:
                    print(f"评论接口错误: {data['message']}")
                    return []
                
                # 处理当前页评论
                for reply in data["data"]["replies"]:
                    if reply.get("content", {}).get("pictures"):
                        all_images.extend(pic["img_src"] for pic in reply["content"]["pictures"])
                    
                    # 处理子评论
                    if reply.get("replies"):
                        for sub_reply in reply["replies"]:
                            if sub_reply.get("content", {}).get("pictures"):
                                all_images.extend(pic["img_src"] for pic in sub_reply["content"]["pictures"])
                
                # 更新分页参数
                if data["data"]["cursor"]["is_end"]:
                    return all_images
                
                next_page = data["data"]["cursor"]["next"]
                time.sleep(0.5)  # 评论请求间隔
                break
                
            except Exception as e:
                print(f"评论请求失败: {str(e)}，剩余重试次数：{retry_count-1}")
                time.sleep(2)
                if _ == retry_count-1:
                    return all_images
                continue

def download_image(url, folder):
    """改进的下载函数"""
    filename = url.split("/")[-1].split("?")[0]
    filepath = os.path.join(folder, filename)
    
    if os.path.exists(filepath):
        print(f"文件已存在: {filename}")
        return
    
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, stream=True, timeout=15)
            response.raise_for_status()
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"下载成功: {filename}")
            return
        except Exception as e:
            print(f"下载失败({attempt+1}/3): {filename} - {str(e)}")
            time.sleep(2)
    
    print(f"无法下载: {filename}")

def main(mid):
    os.makedirs(SAVE_PATH, exist_ok=True)
    
    print("开始获取动态列表...")
    dynamics = get_all_dynamics(mid)
    print(f"共找到 {len(dynamics)} 条动态")
    
    for index, dynamic in enumerate(dynamics, 1):
        try:
            # 生成带连字符的日期格式
            folder_name = dynamic["pub_date"].strftime("%Y-%m-%d")
            save_folder = os.path.join(SAVE_PATH, folder_name)
            os.makedirs(save_folder, exist_ok=True)
            
            print(f"\n处理动态 {index}/{len(dynamics)}")
            print(f"动态ID: {dynamic['oid']} | 类型: {dynamic['type']} | 发布时间: {folder_name}")
            
            images = get_all_replies(dynamic["oid"], dynamic["type"])
            print(f"发现 {len(images)} 张图片")
            
            for img_url in images:
                download_image(img_url, save_folder)
                
        except Exception as e:
            print(f"处理动态 {dynamic['oid']} 时出错: {str(e)}")
            continue

if __name__ == "__main__":
    USER_MID = "560647"
    main(USER_MID)
