import os
import re
import time
import json
import requests
from datetime import datetime
import logging
from urllib.parse import urlparse

# 在此处填写你的微博 Cookie(必需)
COOKIES = ""
#纯文字内容单独存储到一个文件夹

#未下载
#2683370593 谢安然
#2668367923病院坂saki
#1664562813河野華
#2692299095馨心_Mia
#1877891953腥味猫罐
#1909576453走路摇ZLY


#5839848157粽子淞
#6136736001绿子


#已经下载
#1923024604绮太郎
#5491928243 bbb
# 基础配置
DEFAULT_UID = ["6136736001,5839848157"]  # 修改为默认包含多个用户ID
DEFAULT_SAVE_DIR = "D:\\测试"
SESSION = requests.Session()

# URLManager 类保持不变
class URLManager:
    """管理已成功保存的 URL,防止重复下载"""
    def __init__(self):
        self.visited = set()

    def add_url(self, url):
        if url in self.visited:
            return False
        self.visited.add(url)
        return True

    def has_url(self, url):
        return url in self.visited

    def get_all_urls(self):
        return list(self.visited)

# FileManager 类保持不变
class FileManager:
    """管理 URL 文件的加载、追加及更新"""
    @staticmethod
    def load_urls(file_path):
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    @staticmethod
    def append_url(file_path, url):
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(url + "\n")

    @staticmethod
    def update_unsaved_file(file_path, unsaved_set):
        with open(file_path, "w", encoding="utf-8") as f:
            for url in unsaved_set:
                f.write(url + "\n")

# WeiboUtils 类保持不变
class WeiboUtils:
    """工具方法集合"""
    @staticmethod
    def clean_content(content):
        content = re.sub(r'<[^>]+>', '', content)
        cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9_\-\\s]', '', content)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned[:20]

    @staticmethod
    def get_valid_filename(name):
        return re.sub(r'[\\/*?:"<>|]', "", name)

    @staticmethod
    def safe_mkdir(path):
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except OSError:
            base, name = os.path.split(path)
            truncated = name[:50 - len(base) - 1]
            return WeiboUtils.safe_mkdir(os.path.join(base, truncated))

    @staticmethod
    def download_media(url, path):
        if os.path.exists(path):
            return True
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Mi 10) AppleWebKit/537.36 (KHTML, like Gecko)'
                              'Chrome/91.0.4472.124 Mobile Safari/537.36',
                'Referer': 'https://weibo.com/'
            }
            response = SESSION.get(url, headers=headers, stream=True, timeout=20)
            if response.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except Exception as e:
            logging.error(f"下载失败 {url}:{str(e)}")
        return False

# WeiboClient 类保持不变
class WeiboClient:
    """封装微博相关的接口调用与数据解析"""
    def __init__(self, uid):
        self.uid = uid

    def get_containerid(self):
        profile_url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={self.uid}"
        try:
            response = SESSION.get(profile_url, timeout=10)
            data = response.json()
            for tab in data.get('data', {}).get('tabsInfo', {}).get('tabs', []):
                if tab.get('tab_type') == 'weibo':
                    return tab.get('containerid')
        except Exception as e:
            logging.error(f"获取 containerid 失败:{str(e)}")
        return None

    def get_user_screen_name(self):
        """获取用户微博名称"""
        profile_url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={self.uid}"
        try:
            response = SESSION.get(profile_url, timeout=10)
            data = response.json()
            return data.get('data', {}).get('userInfo', {}).get('screen_name', '')
        except Exception as e:
            logging.error(f"获取用户昵称失败:{str(e)}")
            return ''

    def fetch_list(self, containerid, page=1):
        api_url = f"https://m.weibo.cn/api/container/getIndex?containerid={containerid}&page={page}"
        try:
            response = SESSION.get(api_url, timeout=15)
            data = response.json()
            return data.get('data', {}).get('cards', [])
        except Exception as e:
            logging.error(f"获取微博列表失败:{str(e)}")
        return []

    def parse_weibo(self, card):
        if not card.get('mblog'):
            return None
        mblog = card['mblog']
        created_at = mblog.get('created_at', '')
        try:
            dt = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
            time_str = dt.strftime("%Y-%m-%d-%H-%M-%S")
        except:
            time_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        content = WeiboUtils.clean_content(mblog.get('text', ''))
        pics = []
        if 'pics' in mblog:
            for pic in mblog['pics']:
                if 'live_photo' in pic:
                    pics.append({'type': 'live', 'jpg_url': pic['large']['url'], 'mov_url': pic['live_photo']})
                elif 'large' in pic:
                    pics.append({'type': 'image', 'jpg_url': pic['large']['url']})
        retweeted_status = mblog.get('retweeted_status')
        if retweeted_status and 'pics' in retweeted_status:
            for pic in retweeted_status['pics']:
                if 'live_photo' in pic:
                    pics.append({'type': 'live', 'jpg_url': pic['large']['url'], 'mov_url': pic['live_photo']})
                elif 'large' in pic:
                    pics.append({'type': 'image', 'jpg_url': pic['large']['url']})
        video_url = None
        if 'page_info' in mblog and 'media_info' in mblog['page_info']:
            video_info = mblog['page_info']['media_info']
            video_url = video_info.get('stream_url_hd') or video_info.get('stream_url')
        return {
            'time': time_str,
            'content': content,
            'pics': pics,
            'video': video_url,
            'url': f"https://weibo.com/{mblog.get('user', {}).get('id')}/{mblog.get('bid')}"
        }

    #weibo微博保存函数
    def save_weibo(self, weibo, save_dir):
        # 新增逻辑：区分纯文字内容和其他的内容
        if not weibo['pics'] and not weibo['video']:
            base_dir = os.path.join(save_dir, "txt", f"{weibo['time']}-{WeiboUtils.get_valid_filename(weibo['content'])}")
        else:
            base_dir = os.path.join(save_dir, f"{weibo['time']}-{WeiboUtils.get_valid_filename(weibo['content'])}")
        
        actual_path = WeiboUtils.safe_mkdir(base_dir)
        txt_path = os.path.join(actual_path, "content.txt")
        if not os.path.exists(txt_path):
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"内容:{weibo['content']}\n链接:{weibo['url']}")
        
        media_count = 1
        for media in weibo['pics']:
            if media['type'] == 'image':
                media_path = os.path.join(actual_path, f"image_{media_count}.jpg")
                if not WeiboUtils.download_media(media['jpg_url'], media_path):
                    return False
            elif media['type'] == 'live':
                jpg_path = os.path.join(actual_path, f"live_photo_{media_count}.jpg")
                if not WeiboUtils.download_media(media['jpg_url'], jpg_path):
                    return False
                mov_path = os.path.join(actual_path, f"live_photo_{media_count}.mov")
                if not WeiboUtils.download_media(media['mov_url'], mov_path):
                    return False
            media_count += 1
        
        if weibo['video']:
            video_path = os.path.join(actual_path, "video.mp4")
            WeiboUtils.download_media(weibo['video'], video_path)
        return True


class WeiboCrawler:
    """整体爬虫配置"""
    def __init__(self, uid, save_dir, interval):
        self.uid = uid
        self.save_dir = save_dir
        self.interval = interval
        self.client = WeiboClient(uid)
        self.url_manager = URLManager()
        self.saved_urls_file = os.path.join(save_dir, "saved_urls.txt")
        self.unsaved_urls_file = os.path.join(save_dir, "unsaved_urls.txt")
        if not os.path.exists(self.unsaved_urls_file):
            open(self.unsaved_urls_file, "w", encoding="utf-8").close()
        for url in FileManager.load_urls(self.saved_urls_file):
            self.url_manager.add_url(url)
        self.unsaved_set = set(FileManager.load_urls(self.unsaved_urls_file))

    def crawl(self):
        containerid = self.client.get_containerid()
        if not containerid:
            logging.error("无法获取 containerid,请检查 Cookie 和 用户ID")
            return

        total = 0
        success = 0
        failed = 0
        page = 1
        start_time = time.time()

        while True:
            logging.info(f"正在获取第 {page} 页数据...")
            cards = self.client.fetch_list(containerid, page)
            if not cards:
                logging.info("没有更多数据")
                break

            for card in cards:
                if card.get('card_type') != 9:
                    continue
                weibo = self.client.parse_weibo(card)
                if not weibo:
                    continue
                url = weibo['url']
                if self.url_manager.has_url(url):
                    logging.info(f"这条已经保存:{url}")
                    continue

                total += 1
                try:
                    if self.client.save_weibo(weibo, self.save_dir):
                        success += 1
                        logging.info(f"成功保存:{weibo['content']}")
                        self.url_manager.add_url(url)
                        FileManager.append_url(self.saved_urls_file, url)
                        if url in self.unsaved_set:
                            self.unsaved_set.remove(url)
                            FileManager.update_unsaved_file(self.unsaved_urls_file, self.unsaved_set)
                    else:
                        failed += 1
                        logging.error(f"保存失败:{url}")
                        if url not in self.unsaved_set:
                            self.unsaved_set.add(url)
                            FileManager.update_unsaved_file(self.unsaved_urls_file, self.unsaved_set)
                    time.sleep(self.interval)
                except Exception as e:
                    logging.error(f"保存异常:{str(e)}")
                    failed += 1

            page += 1
            time.sleep(self.interval + 2)

        elapsed = time.time() - start_time
        logging.info("\n====== 统计结果 ======")
        logging.info(f"总计处理:{total} 条")
        logging.info(f"成功保存:{success} 条")
        logging.info(f"失败数量:{failed} 条")
        logging.info(f"耗时:{elapsed:.2f} 秒")

# setup_logger 函数保持不变
def setup_logger(save_dir):
    log_file = os.path.join(save_dir, f"weibo_crawler_{datetime.now().strftime('%Y%m%d%H%M')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return log_file

# 修改 main 函数以支持批量爬取
# 修改 main 函数以支持批量爬取
def main():
    print("赵喵喵5839848157 半年可见")
    print("Kitaro绮太郎1923024604 半年可见")
    print("坂坂白 5491928243 半年可见\n")
    
    # 处理用户输入
    default_uid_str = ','.join(DEFAULT_UID)
    uid_input = input(f"请输入用户ID(多个ID用逗号分隔,默认{default_uid_str}): ").strip()
    if uid_input:
        uid_list = [uid.strip() for uid in uid_input.split(',')]
    else:
        uid_list = DEFAULT_UID.copy()
    
    save_dir = input(f"请输入保存目录(默认{DEFAULT_SAVE_DIR}): ") or DEFAULT_SAVE_DIR
    interval = int(input("请输入请求间隔(秒,默认5): ") or 5)

    # 初始化 SESSION
    SESSION.headers.update({
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Mi 10) AppleWebKit/537.36 (KHTML, like Gecko)'
                      'Chrome/91.0.4472.124 Mobile Safari/537.36',
        'Cookie': COOKIES
    })

    # 遍历每个用户ID，进行爬取
    for uid in uid_list:
        client = WeiboClient(uid)
        screen_name = client.get_user_screen_name()
        
        # 处理昵称为空的情况
        if not screen_name:
            screen_name = f"unknown_{uid}"
        
        # 生成 screen_name_uid 格式的目录名
        folder_name = f"{WeiboUtils.get_valid_filename(screen_name)}_{uid}"
        user_save_dir = os.path.join(save_dir, folder_name)
        os.makedirs(user_save_dir, exist_ok=True)
        
        # 设置日志
        setup_logger(user_save_dir)
        
        # 创建并运行爬虫
        crawler = WeiboCrawler(uid, user_save_dir, interval)
        crawler.crawl()
        print(f"{folder_name} 遍历结束------------------")

if __name__ == "__main__":
    main()
