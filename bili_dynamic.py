import os
import re
import json
import time
import requests
import datetime
import random

def load_config():
    """加载配置文件 config.json。如果不存在或缺少键，则报错退出。"""
    config_path = 'config.json'
    if not os.path.exists(config_path):
        print(f"错误: 配置文件 {config_path} 不存在。")
        print("请创建一个 config.json 文件并填入所有必需的配置信息。")
        exit()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 检查所有必需的键是否存在
        required_keys = ["COOKIE", "default_uid", "interval", "base_dir"]
        missing_keys = [key for key in required_keys if key not in config_data]
        if missing_keys:
            print(f"错误: 您的 config.json 文件中缺少以下必要的键: {', '.join(missing_keys)}")
            exit()
            
        return config_data
    except json.JSONDecodeError:
        print(f"错误: {config_path} 文件格式不正确，无法解析JSON。")
        exit()
    except Exception as e:
        print(f"加载配置文件时发生未知错误: {e}")
        exit()

class Config:
    def __init__(self, settings):
        self.settings = settings
        self.COOKIE = self.get_cookie()
        
        # 直接从 settings (config.json) 加载配置，不再使用 input
        self.base_dir = self.settings["base_dir"]
        self.interval = self.settings["interval"]
        self.uid_list = self.get_uid_list()
        
        print("配置加载成功:")
        print(f" - UID列表: {self.uid_list}")
        print(f" - 下载间隔: {self.interval} 秒")
        print(f" - 保存基目录: {self.base_dir}")

        self.uid = None
        self.download_dir = None
        self.username = None
        self.username_cache = {}
        self.saved_url_filename = None
        self.unsaved_url_filename = None
        self.date_log_filename = None

        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_cookie(self):
        """从配置中获取COOKIE，如果长度不足则提示用户在终端输入。"""
        cookie = self.settings.get("COOKIE", "")
        cookie_length = 100
        if len(cookie) > cookie_length:
            return cookie
        else:
            while len(cookie) < cookie_length:
                print("config.json中的COOKIE长度太短,可能是错误的,请在下方终端重新输入。")
                cookie = input("请输入B站Cookie(必填): ").strip()
            return cookie

    def get_uid_list(self):
        """从配置中解析UID列表。"""
        default_uid_list = self.settings.get("default_uid", [])
        parsed_uids = [item.split('_')[-1] for item in default_uid_list if item.split('_')[-1].isdigit()]
        
        if not parsed_uids:
            print("警告: 在 config.json 中没有找到有效的UID。'default_uid' 列表为空或格式不正确 (应为 '用户名_UID' 格式)。")
        
        return parsed_uids

    def get_username(self, uid):
        if uid in self.username_cache:
            return self.username_cache[uid]
        url = f"https://api.bilibili.com/x/space/acc/info?mid={uid}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Cookie": self.COOKIE
        }
        try:
            time.sleep(3)
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    username = data.get("data", {}).get("name", f"用户_{uid}")
                    self.username_cache[uid] = username
                    return username
                else:
                    print(f"获取用户名失败: {data.get('message')}")
            else:
                print(f"API请求失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"获取用户名异常: {e}")
        return f"用户_{uid}"

    def get_download_dir(self, base_dir, uid):
        for subdir in os.listdir(base_dir):
            subdir_path = os.path.join(base_dir, subdir)
            if os.path.isdir(subdir_path) and uid in subdir:
                print(f'检测到同名"{uid}",跳过通过api获取用户名')
                return subdir_path
        username = self.get_username(uid)
        new_folder_name = f"{username}_{uid}"
        new_folder_path = os.path.join(base_dir, new_folder_name)
        os.makedirs(new_folder_path, exist_ok=True)
        print(f"创建新文件夹: {new_folder_path}")
        return new_folder_path

    def update_for_uid(self, uid):
        self.uid = uid
        self.download_dir = self.get_download_dir(self.base_dir, uid)
        self.username = self.get_username(uid)
        self.saved_url_filename = os.path.join(self.download_dir, "saved_url.txt")
        self.unsaved_url_filename = os.path.join(self.download_dir, "unsaved_url.txt")
        self.date_log_filename = os.path.join(self.download_dir, "date.log")
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

class FileManager:
    def __init__(self, config: Config):
        self.config = config
        self.ensure_file_exists(self.config.saved_url_filename)
        self.ensure_file_exists(self.config.unsaved_url_filename)
        self.ensure_file_exists(self.config.date_log_filename)

    def ensure_file_exists(self, filename):
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                pass

    def load_url_set(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return {line.strip() for line in f if line.strip()}
        return set()

    def write_url_file(self, filename, urls):
        with open(filename, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url + "\n")

    def read_date_log(self):
        """只读取 date.log 第一行的数字作为截止时间"""
        if os.path.exists(self.config.date_log_filename):
            with open(self.config.date_log_filename, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                if lines and lines[0].isdigit():
                    return int(lines[0])
        return None

    def read_date_log_lines(self):
        """读取 date.log 中的所有日期，返回列表"""
        if os.path.exists(self.config.date_log_filename):
            with open(self.config.date_log_filename, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                return [int(line) for line in lines if line.isdigit()]
        return []

    def write_sorted_date_log(self, date_list):
        """将排序后的日期列表写入 date.log"""
        sorted_dates = sorted(date_list, reverse=True)
        with open(self.config.date_log_filename, 'w', encoding='utf-8') as f:
            for date in sorted_dates:
                f.write(str(date) + "\n")

class Utils:
    ILLEGAL_CHAR_PATTERN = r'[#@.<>:"/\\|?*\n\r]'

    @staticmethod
    def sanitize_filename(name, max_length):
        name = re.sub(Utils.ILLEGAL_CHAR_PATTERN, '', name)
        name = re.sub(r'\s+', ' ', name)
        name = name.strip(" .")
        if len(name) > max_length:
            name = name[:max_length].rstrip(" .")
        return name

    @staticmethod
    def parse_dynamic_card(card_str):
        try:
            return json.loads(card_str)
        except Exception as e:
            print("解析 card 失败:", e)
            return {}

    @staticmethod
    def format_datetime(timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp)
        return f"{dt.year}-{dt.month}-{dt.day}-{dt.hour:02d}-{dt.minute:02d}"

    @staticmethod
    def timestamp_to_num(timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp)
        return int(f"{dt.year:04d}{dt.month:02d}{dt.day:02d}{dt.hour:02d}{dt.minute:02d}")

class Downloader:
    def __init__(self, config: Config):
        self.config = config
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
            "Cookie": config.COOKIE
        }

    def download_file(self, url, filepath):
        try:
            delay_first = self.config.settings.get("DELAY_FIRST", 0.1)
            delay_last = self.config.settings.get("DELAY_LAST", 0.2)
            time.sleep(random.uniform(delay_first, delay_last))
            
            r = requests.get(url, headers=self.headers, stream=True, timeout=10)
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                print(f"保存文件: {filepath}")
            else:
                print(f"下载失败 {url} 状态码: {r.status_code}")
        except Exception as e:
            print(f"下载 {url} 出错: {e}")

class DynamicProcessor:
    def __init__(self, config: Config, file_manager: FileManager, downloader: Downloader, saved_url_set: set, date_log_num: int, method: str):
        self.config = config
        self.file_manager = file_manager
        self.downloader = downloader
        self.saved_url_set = saved_url_set
        self.date_log_num = date_log_num
        self.method = method
        self.txt_folder = os.path.join(self.config.download_dir, "txt")
        if not os.path.exists(self.txt_folder):
            os.makedirs(self.txt_folder)

    def process_dynamic(self, dynamic, success_list, failed_list):
        dynamic_url = None
        try:
            desc = dynamic.get("desc", {})
            dynamic_id = desc.get("dynamic_id")
            if not dynamic_id:
                print("无法获取 dynamic_id, 跳过该动态")
                return
            dynamic_id = str(dynamic_id)
            dynamic_url = f"https://t.bilibili.com/{dynamic_id}"

            if self.method == 'url' and dynamic_url in self.saved_url_set:
                print(f"动态 {dynamic_url} 已下载, 跳过。")
                return

            timestamp = desc.get("timestamp")
            if not timestamp:
                print("无法获取 timestamp, 跳过该动态")
                return
            dynamic_time_num = Utils.timestamp_to_num(timestamp)

            if self.method == 'date' and self.date_log_num and dynamic_time_num < self.date_log_num:
                print(f"动态 {dynamic_url} 的发布时间 {dynamic_time_num} 早于截止日期 {self.date_log_num}, 停止爬取")
                raise StopIteration("已经到了截止日期")

            time_str = Utils.format_datetime(timestamp)
            card_str = dynamic.get("card", "")
            card_dict = Utils.parse_dynamic_card(card_str)
            
            file_name_max_length = self.config.settings.get("FILE_NAME_MAX_LENGTH", 40)

            dynamic_content = ""
            if "item" in card_dict:
                item = card_dict["item"]
                dynamic_content = item.get("description", item.get("content", ""))

            has_content = bool(dynamic_content.strip())
            pics = card_dict.get("item", {}).get("pictures", [])

            if not pics:
                if has_content:
                    content_clean = Utils.sanitize_filename(dynamic_content, file_name_max_length)
                    txt_filename = f"{time_str}-{content_clean}.txt"
                else:
                    txt_filename = f"{time_str}-{dynamic_id}.txt"
                txt_path = os.path.join(self.txt_folder, txt_filename)
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(f"URL: {dynamic_url}\n")
                    f.write(f"发布时间: {time_str}\n")
                    f.write("内容:\n")
                    f.write(dynamic_content)
                print(f"保存无图片动态到: {txt_path}")
            else:
                if has_content:
                    content_clean = Utils.sanitize_filename(dynamic_content, file_name_max_length)
                    folder_name = f"{time_str}-{content_clean}".replace(" ", "-")
                    folder_name = Utils.sanitize_filename(folder_name, file_name_max_length)
                    dynamic_folder = os.path.join(self.config.download_dir, folder_name)
                else:
                    null_folder = os.path.join(self.config.download_dir, "null")
                    if not os.path.exists(null_folder):
                        os.makedirs(null_folder)
                    dynamic_folder = os.path.join(null_folder, dynamic_id)

                if not os.path.isdir(dynamic_folder):
                    if os.path.exists(dynamic_folder):
                        os.remove(dynamic_folder)
                    os.makedirs(dynamic_folder)
                    print(f"创建文件夹: {dynamic_folder}")
                else:
                    print(f"文件夹已存在: {dynamic_folder}")

                info_path = os.path.join(dynamic_folder, "info.txt")
                with open(info_path, 'w', encoding='utf-8') as f:
                    f.write(f"URL: {dynamic_url}\n")
                    f.write(f"发布时间: {time_str}\n")
                    f.write("内容:\n")
                    f.write(dynamic_content)
                print(f"保存动态信息到: {info_path}")

                for idx, pic in enumerate(pics, start=1):
                    img_url = pic.get("img_src")
                    if not img_url:
                        continue
                    ext = os.path.splitext(img_url)[1] or ".jpg"
                    img_filename = f"{idx}{ext}"
                    img_path = os.path.join(dynamic_folder, img_filename)
                    print(f"下载图片: {img_url}")
                    self.downloader.download_file(img_url, img_path)

            self.saved_url_set.add(dynamic_url)
            with open(self.config.saved_url_filename, 'a', encoding='utf-8') as f:
                f.write(dynamic_url + "\n")
            success_list.append(dynamic_url)

            with open(self.config.date_log_filename, 'a', encoding='utf-8') as f:
                f.write(str(dynamic_time_num) + "\n")
        except StopIteration as e:
            raise e
        except Exception as e:
            print("处理动态出错:", e)
            if dynamic_url:
                with open(self.config.unsaved_url_filename, 'a', encoding='utf-8') as f:
                    f.write(dynamic_url + "\n")
                failed_list.append(dynamic_url)

class BilibiliDynamicSpider:
    def __init__(self, config: Config, file_manager: FileManager, dynamic_processor: DynamicProcessor):
        self.config = config
        self.file_manager = file_manager
        self.dynamic_processor = dynamic_processor
        self.saved_url_set = self.file_manager.load_url_set(self.config.saved_url_filename)
        self.dynamic_processor.saved_url_set = self.saved_url_set
        self.success_list = []
        self.failed_list = []

    def run(self):
        base_url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history"
        params = {"host_uid": self.config.uid, "offset_dynamic_id": 0}
        has_more = True
        page_count = 1

        try:
            while has_more:
                print(f"正在处理第 {page_count} 页动态...")
                try:
                    response = requests.get(base_url, headers=self.dynamic_processor.downloader.headers, params=params, timeout=10)
                    if response.status_code != 200:
                        print("请求失败, 状态码:", response.status_code)
                        break
                    data = response.json()
                    if data.get("code") != 0:
                        print("接口返回错误信息:", data.get("message", ""))
                        break
                    data_data = data.get("data", {})
                    cards = data_data.get("cards", [])
                    has_more = data_data.get("has_more", False)
                    if "next_offset" in data_data:
                        params["offset_dynamic_id"] = data_data["next_offset"]
                    elif cards:
                        params["offset_dynamic_id"] = cards[-1].get("desc", {}).get("dynamic_id", 0)
                    else:
                        has_more = False

                    if not cards:
                        print("当前页没有动态数据, 结束下载。")
                        break

                    for dynamic in cards:
                        self.dynamic_processor.process_dynamic(dynamic, self.success_list, self.failed_list)

                    page_count += 1
                    print(f"等待 {self.config.interval} 秒后继续下载下一页...")
                    time.sleep(self.config.interval)
                except StopIteration as e:
                    print(e)
                    break
        finally:
            date_list = self.file_manager.read_date_log_lines()
            self.file_manager.write_sorted_date_log(date_list)
            print("date.log 已排序并保存")

class RetryFailedUrls:
    def __init__(self, config: Config, file_manager: FileManager, dynamic_processor: DynamicProcessor):
        self.config = config
        self.file_manager = file_manager
        self.dynamic_processor = dynamic_processor
        self.success_list = []
        self.failed_list = []
        self.headers = {
            **dynamic_processor.downloader.headers,
            "Referer": "https://t.bilibili.com/"
        }

    def run(self):
        print("\n开始重试未成功下载的URL...")
        unsaved_urls = self.file_manager.load_url_set(self.config.unsaved_url_filename)
        if not unsaved_urls:
            print("没有需要重试的URL")
            return
        print(f"发现 {len(unsaved_urls)} 条待重试URL")
        
        still_failed = set()
        success_count = 0
        
        for url in unsaved_urls:
            time.sleep(random.uniform(1.0, 2.0))
            dynamic_id = url.split("/")[-1].split("?")[0]
            if not dynamic_id.isdigit():
                still_failed.add(url)
                continue

            api_url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id={dynamic_id}"
            try:
                res = requests.get(api_url, headers=self.headers, timeout=10)
                detail_data = res.json()
                if detail_data.get('code') == 0:
                    item = detail_data.get('data', {}).get('item', {})
                    if not item:
                         still_failed.add(url)
                         continue
                    
                    # 模拟 space_history 的格式
                    dynamic_card = {
                        "desc": item.get('desc'), 
                        "card": item.get('card') # card在这里是dict, process_dynamic需要str
                    }
                    # 修正：DynamicProcessor 需要 card 是一个字符串
                    dynamic_card['card'] = json.dumps(dynamic_card['card'], ensure_ascii=False)
                    
                    self.dynamic_processor.process_dynamic(dynamic_card, self.success_list, self.failed_list)
                    success_count += 1
                else:
                    print(f"重试URL {url} 失败: {detail_data.get('message')}")
                    still_failed.add(url)
            except Exception as e:
                print(f"重试URL {url} 发生异常: {e}")
                still_failed.add(url)
        
        self.file_manager.write_url_file(self.config.unsaved_url_filename, list(still_failed))
        print(f"\n{'='*30}")
        print(f"重试完成! 成功 {success_count}/{len(unsaved_urls)} 条")
        if still_failed:
            print(f"以下 {len(still_failed)} 个URL仍然失败:\n" + "\n".join(still_failed))


class OperationMenu:
    def __init__(self, config: Config, downloader: Downloader):
        self.config = config
        self.downloader = downloader

    def run(self):
        while True:
            choice = input(
                "\n请选择操作:\n"
                "1. 开始新抓取\n"
                "2. 重试失败URL\n"
                "3. 退出\n"
                "4. (从config.json)重新加载UID列表\n请输入数字: "
            ).strip()
            if choice == "1":
                method_choice = input(
                    "请选择保存方法:\n"
                    "1. 使用 date.log 截止日期停止 (推荐)\n"
                    "2. 检查 saved_url.txt，直到获取到已保存的URL\n"
                    "请输入数字: "
                ).strip()
                method = 'date' if method_choice == "1" else 'url'
                
                for uid in self.config.uid_list:
                    print(f"\n{'='*20}\n开始下载UID: {uid} ({self.config.get_username(uid)})\n{'='*20}")
                    self.config.update_for_uid(uid)
                    file_manager = FileManager(self.config)
                    date_log_num = file_manager.read_date_log()
                    saved_url_set = file_manager.load_url_set(self.config.saved_url_filename)
                    dynamic_processor = DynamicProcessor(self.config, file_manager, self.downloader, saved_url_set, date_log_num, method)
                    spider = BilibiliDynamicSpider(self.config, file_manager, dynamic_processor)
                    spider.run()
                    long_interval = self.config.settings.get("LONG_LONG_INTERVAL", 1200) / len(self.config.uid_list)
                    long_interval = min(max(long_interval, 3.0), 30.0)
                    print(f"\n用户 {uid} 下载完成，暂停 {long_interval:.2f} 秒\n")
                    time.sleep(long_interval)
            elif choice == "2":
                for uid in self.config.uid_list:
                    print(f"\n{'='*20}\n重试UID: {uid} 的失败URL\n{'='*20}")
                    self.config.update_for_uid(uid)
                    file_manager = FileManager(self.config)
                    date_log_num = None 
                    saved_url_set = file_manager.load_url_set(self.config.saved_url_filename)
                    dynamic_processor = DynamicProcessor(self.config, file_manager, self.downloader, saved_url_set, date_log_num, method='url')
                    retry = RetryFailedUrls(self.config, file_manager, dynamic_processor)
                    retry.run()
            elif choice == "3":
                print("程序退出")
                break
            elif choice == "4":
                print("从 config.json 重新加载UID列表...")
                self.config.uid_list = self.config.get_uid_list()
                print(f"UID列表已更新为: {self.config.uid_list}")
            else:
                print("无效输入，请重新选择")

def main():
    app_settings = load_config()
    config = Config(app_settings)
    downloader = Downloader(config)
    menu = OperationMenu(config, downloader)
    menu.run()

if __name__ == "__main__":
    main()