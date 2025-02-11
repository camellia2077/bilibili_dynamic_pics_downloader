import os
import requests
import json
import random
import time
from datetime import datetime
#class
class Config:
    """全局配置类"""
    USER_MID = "560647"  # 默认用户UID
    COOKIE = ""
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Cookie": COOKIE
    }
    SAVE_PATH = "C:\\Base1\\bbb\\bili_comment"
    DELAY_RANGE = (0.5, 0.6)  # 随机延迟范围
    DYNAMIC_TYPE_MAP = {
        "DYNAMIC_TYPE_DRAW": 11,
        "DYNAMIC_TYPE_WORD": 17,
        "DYNAMIC_TYPE_FORWARD": 17
    }

class APIClient:
    """API请求客户端"""
    def __init__(self):
        self.headers = Config.HEADERS
        self.delay_range = Config.DELAY_RANGE
    
    def _random_delay(self):
        """生成随机延迟"""
        time.sleep(random.uniform(*self.delay_range))
    
    def fetch_dynamic_page(self, offset):
        """
        获取单页动态数据
        :param offset: 分页偏移量
        :return: (has_more, next_offset, items)
        """
        self._random_delay()
        try:
            response = requests.get(
                url="https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space",
                headers=self.headers,
                params={"host_mid": Config.USER_MID, "offset": offset},
                timeout=15
            )
            response.raise_for_status()
            data = json.loads(response.text)
            
            if data["code"] != 0:
                print(f"动态接口错误: {data['message']}")
                return False, None, []
            
            return (
                data["data"]["has_more"],
                data["data"]["offset"],
                data["data"]["items"]
            )
        except Exception as e:
            print(f"动态页请求失败: {str(e)}")
            return False, None, []
    
    def fetch_comments(self, oid, dynamic_type, next_page=0):
        """
        获取评论数据
        :param oid: 动态ID
        :param dynamic_type: 动态类型
        :param next_page: 分页页码
        :return: (is_end, next_page, replies)
        """
        self._random_delay()
        try:
            response = requests.get(
                url="https://api.bilibili.com/x/v2/reply/main",
                headers=self.headers,
                params={
                    "type": dynamic_type,
                    "oid": oid,
                    "mode": 3,
                    "next": next_page
                },
                timeout=10
            )
            response.raise_for_status()
            data = json.loads(response.text)
            
            if data["code"] != 0:
                print(f"评论接口错误: {data['message']}")
                return True, 0, []
            
            return (
                data["data"]["cursor"]["is_end"],
                data["data"]["cursor"]["next"],
                data["data"]["replies"]
            )
        except Exception as e:
            print(f"评论请求失败: {str(e)}")
            return True, 0, []

class DynamicProcessor:
    """动态处理器"""
    def __init__(self, api_client):
        self.api_client = api_client
    
    def parse_dynamic_item(self, item):
        """
        解析单个动态项
        :return: (oid, pub_date, dynamic_type)
        """
        try:
            dynamic_type = Config.DYNAMIC_TYPE_MAP.get(item["type"], 17)
            if dynamic_type == 11:
                oid = item["modules"]["module_dynamic"]["major"]["draw"]["id"]
            else:
                oid = item["id_str"]
            
            pub_date = datetime.fromtimestamp(
                item["modules"]["module_author"]["pub_ts"]
            )
            return oid, pub_date, dynamic_type
        except KeyError as e:
            print(f"动态解析失败: {str(e)}")
            return None, None, None

class ImageDownloader:
    """图片下载器"""
    def __init__(self):
        self.base_path = Config.SAVE_PATH
    
    def create_folder(self, pub_date):
        """
        创建保存目录
        :return: 完整保存路径
        """
        folder_name = pub_date.strftime("%Y-%m-%d")
        full_path = os.path.join(self.base_path, folder_name)
        os.makedirs(full_path, exist_ok=True)
        return full_path
    
    def download(self, url, save_path, retry=3):
        """
        下载单张图片
        :return: 是否下载成功
        """
        filename = url.split("/")[-1].split("?")[0]
        filepath = os.path.join(save_path, filename)
        
        if os.path.exists(filepath):
            return False
        
        for attempt in range(retry):
            try:
                response = requests.get(url, headers=Config.HEADERS, stream=True, timeout=20)
                response.raise_for_status()
                
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"下载成功: {filename}")
                return True
            except Exception as e:
                print(f"下载失败({attempt+1}/{retry}): {filename}")
                time.sleep(1)
        
        print(f"永久下载失败: {filename}")
        return False

class MainController:
    """主控制器"""
    def __init__(self):
        self.api_client = APIClient()
        self.dynamic_processor = DynamicProcessor(self.api_client)
        self.downloader = ImageDownloader()
    
    def process_all_dynamics(self):
        """处理所有动态"""
        offset = ""
        page_num = 1
        
        while True:
            print(f"\n正在获取第 {page_num} 页动态...")
            has_more, new_offset, items = self.api_client.fetch_dynamic_page(offset)
            
            if not items:
                print("等待5秒后重试...")
                time.sleep(5)
                continue
            
            # 处理本页动态
            for item in items:
                self.process_single_dynamic(item)
            
            if not has_more:
                print("\n所有动态已处理完毕")
                break
            
            offset = new_offset
            page_num += 1
            time.sleep(random.uniform(1.0, 1.5))
    
    def process_single_dynamic(self, item):
        """处理单个动态"""
        oid, pub_date, dynamic_type = self.dynamic_processor.parse_dynamic_item(item)
        if not all([oid, pub_date, dynamic_type]):
            return
        
        print(f"\n处理动态 {oid} ({pub_date})")
        
        # 获取图片
        images = self._get_all_images(oid, dynamic_type)
        print(f"发现 {len(images)} 张图片")
        
        # 下载图片
        save_folder = self.downloader.create_folder(pub_date)
        for idx, img_url in enumerate(images, 1):
            self.downloader.download(img_url, save_folder)
            if idx % 5 == 0:
                time.sleep(random.uniform(*Config.DELAY_RANGE))
    
    def _get_all_images(self, oid, dynamic_type):
        """获取动态所有图片"""
        images = []
        next_page = 0
        
        while True:
            is_end, new_page, replies = self.api_client.fetch_comments(oid, dynamic_type, next_page)
            
            # 提取图片
            for reply in replies:
                images += self._extract_images(reply)
                for sub_reply in reply.get("replies", []):
                    images += self._extract_images(sub_reply)
            
            if is_end:
                break
            
            next_page = new_page
        
        return images
    
    def _extract_images(self, reply):
        """从回复中提取图片"""
        if "content" in reply and "pictures" in reply["content"]:
            return [pic["img_src"] for pic in reply["content"]["pictures"]]
        return []

def main():
    """程序入口"""
    controller = MainController()
    print(f"开始爬取用户 {Config.USER_MID} 的动态...")
    controller.process_all_dynamics()

if __name__ == "__main__":
    main()
