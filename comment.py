import os
import requests
import json
import random
import time
from datetime import datetime
#全局变量延迟
# 全局配置
COOKIE = ""
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Cookie": COOKIE
}
SAVE_PATH = "C:\Base1\srt"
DELAY_FIRST = 0.5  # 最小延迟时间（秒）
DELAY_LAST = 0.6   # 最大延迟时间（秒）

DYNAMIC_TYPE_MAP = {
    "DYNAMIC_TYPE_DRAW": 11,
    "DYNAMIC_TYPE_WORD": 17,
    "DYNAMIC_TYPE_FORWARD": 17
}

def random_delay():
    """生成随机延迟"""
    time.sleep(random.uniform(DELAY_FIRST, DELAY_LAST))

def process_single_page(mid, offset):
    """处理单页动态并返回下一页offset（带延迟）"""
    url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
    params = {"host_mid": mid, "offset": offset}
    
    try:
        # 添加请求前延迟
        random_delay()
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
        data = json.loads(response.text)
        
        if data["code"] != 0:
            print(f"动态列表接口错误: {data['message']}")
            return None, None
        
        # 处理本页动态
        for item in data["data"]["items"]:
            process_single_dynamic(item)
        
        # 返回下一页参数
        return data["data"]["has_more"], data["data"]["offset"]
    
    except Exception as e:
        print(f"动态页请求失败: {str(e)}")
        return None, None

def process_single_dynamic(item):
    """处理单个动态（带延迟）"""
    try:
        # 解析动态信息
        dynamic_type = DYNAMIC_TYPE_MAP.get(item["type"], 17)
        oid = item["modules"]["module_dynamic"]["major"]["draw"]["id"] if dynamic_type == 11 else item["id_str"]
        pub_date = datetime.fromtimestamp(item["modules"]["module_author"]["pub_ts"])
        
        # 创建日期目录
        folder_name = pub_date.strftime("%Y-%m-%d")
        save_folder = os.path.join(SAVE_PATH, folder_name)
        os.makedirs(save_folder, exist_ok=True)
        
        print(f"\n开始处理动态 {oid} ({pub_date})")
        
        # 获取并下载图片
        images = get_all_replies(oid, dynamic_type)
        print(f"发现 {len(images)} 张图片")
        
        for idx, img_url in enumerate(images, 1):
            download_image(img_url, save_folder)
            # 每下载5张添加额外延迟
            if idx % 5 == 0:
                random_delay()
    
    except Exception as e:
        print(f"处理动态失败: {str(e)}")

def get_all_replies(oid, dynamic_type):
    """获取全部评论图片（带延迟）"""
    images = []
    next_page = 0
    retry_count = 3
    
    while True:
        # 使用新版评论接口
        url = "https://api.bilibili.com/x/v2/reply/main"
        params = {
            "type": dynamic_type,
            "oid": oid,
            "mode": 3,
            "next": next_page
        }
        
        success = False
        for _ in range(retry_count):
            try:
                random_delay()  # 评论请求前延迟
                response = requests.get(url, headers=HEADERS, params=params, timeout=10)
                response.raise_for_status()
                data = json.loads(response.text)
                
                if data["code"] != 0:
                    print(f"评论接口错误: {data['message']}")
                    return images
                
                # 提取图片
                for reply in data["data"]["replies"]:
                    images += extract_images_from_reply(reply)
                    # 处理子评论
                    for sub_reply in reply.get("replies", []):
                        images += extract_images_from_reply(sub_reply)
                
                # 检查是否结束
                if data["data"]["cursor"]["is_end"]:
                    return images
                
                next_page = data["data"]["cursor"]["next"]
                success = True
                break
                
            except Exception as e:
                print(f"评论请求失败: {str(e)}，剩余重试次数：{retry_count-1}")
                time.sleep(2)
        
        if not success:
            print("评论请求最终失败，跳过本动态")
            return images

def extract_images_from_reply(reply):
    """从回复中提取图片"""
    if "content" in reply and "pictures" in reply["content"]:
        return [pic["img_src"] for pic in reply["content"]["pictures"]]
    return []

def download_image(url, folder):
    """增强版下载函数（带延迟）"""
    filename = url.split("/")[-1].split("?")[0]
    filepath = os.path.join(folder, filename)
    
    if os.path.exists(filepath):
        return
    
    for attempt in range(3):
        try:
            random_delay()  # 下载前延迟
            response = requests.get(url, headers=HEADERS, stream=True, timeout=20)
            response.raise_for_status()
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"√ 下载成功: {filename}")
            return
        except Exception as e:
            print(f"× 下载失败({attempt+1}/3): {filename}")
            time.sleep(1)
    
    print(f"! 永久下载失败: {filename}")

def main(mid):
    os.makedirs(SAVE_PATH, exist_ok=True)
    has_more = True
    offset = ""
    page_num = 1
    
    while has_more:
        print(f"\n正在获取第 {page_num} 页动态...")
        has_more, new_offset = process_single_page(mid, offset)
        
        if has_more is None:  # 出错重试
            print("等待5秒后重试本页...")
            time.sleep(5)
            continue
        
        if has_more:
            offset = new_offset
            page_num += 1
            # 动态翻页后延迟
            time.sleep(random.uniform(1.0, 1.5))  # 翻页大间隔
        else:
            print("\n所有动态已处理完毕")

if __name__ == "__main__":
    USER_MID = "560647"
    main(USER_MID)
