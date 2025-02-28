import os
import re
import json
import time
import requests
import datetime
import random

FILE_NAME_MAX_LENGTH = 40
COOKIE = "fucj"
DELAY_FIRST = 0.5
DELAY_LAST = 0.6
LONG_LONG_INTERVAL = 1200

class Config:
    def __init__(self, uid_list=None):
        self.COOKIE = self.get_cookie()
        self.uid_list = uid_list if uid_list else self.get_uid_list()
        self.uid = None
        self.download_dir = None
        self.username = None
        self.interval = self.get_interval()
        self.username_cache = {}
        self.saved_url_filename = None
        self.unsaved_url_filename = None
        self.date_log_filename = None
        base_dir_input = input("请输入保存文件的基目录（默认 C:\\Base1\\bili）:").strip()
        self.base_dir = base_dir_input if base_dir_input else "C:\\Base1\\bili"
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_cookie(self):
        global COOKIE
        cookie_length = 100
        if len(COOKIE) > cookie_length:
            return COOKIE
        else:
            while len(COOKIE) < 100:
                print(f"cookie小于{100},全局变量COOKIE的长度太短,应该是错误的,请重新输入")
                COOKIE = input("请输入B站Cookie(必填):").strip()
            return COOKIE

    def get_uid_list(self):
        
        default_uid = ["2075682", "8048877", "560647", 
                       "4096581", "18343098", "21876627", 
                       "305956876", "498099165", "31968078",
                       "356010767"]
        result = ",".join(default_uid)
        print(f"回车默认下载为:{result}")
        uid_input = input(f"请输入用户UID,多个UID用逗号分隔:").strip()
        if uid_input:
            uid_list = [uid.strip() for uid in uid_input.split(',')]
        else:
            uid_list = default_uid
        return uid_list

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

    def get_interval(self):
        user_interval = input("请输入float类型下载间隔(秒，默认3):").strip()
        if user_interval == "":
            return 3
        else:
            float_user_interval = float(user_interval)
            print("您现在输入的的间隔是:", float_user_interval, "秒")
            return float_user_interval

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
            time.sleep(random.uniform(DELAY_FIRST, DELAY_LAST))
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

            dynamic_content = ""
            if "item" in card_dict:
                item = card_dict["item"]
                dynamic_content = item.get("description", item.get("content", ""))

            has_content = bool(dynamic_content.strip())
            pics = card_dict.get("item", {}).get("pictures", [])

            if not pics:
                if has_content:
                    content_clean = Utils.sanitize_filename(dynamic_content, FILE_NAME_MAX_LENGTH)
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
                    content_clean = Utils.sanitize_filename(dynamic_content, FILE_NAME_MAX_LENGTH)
                    folder_name = f"{time_str}-{content_clean}".replace(" ", "-")
                    folder_name = Utils.sanitize_filename(folder_name, FILE_NAME_MAX_LENGTH)
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
            # 追加日期到 date.log
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

    def _get_dynamic_detail(self, dynamic_id):
        api_url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail"
        params = {"dynamic_id": dynamic_id}
        try:
            response = requests.get(api_url, headers=self.headers, params=params, timeout=10)
            if response.status_code != 200:
                print(f"请求失败 状态码: {response.status_code}")
                return None
            data = response.json()
            if data.get("code") != 0:
                print(f"接口返回错误: {data.get('message')}")
                return None
            return data.get("data", {}).get("card")
        except Exception as e:
            print(f"获取动态详情失败: {e}")
            return None

    def _process_single_url(self, url):
        print(f"\n{'='*30}\n正在处理URL: {url}")
        if not url.startswith("https://t.bilibili.com/"):
            print("非标准动态URL，跳过")
            return False
        dynamic_id = url.split("/")[-1]
        if not dynamic_id.isdigit():
            print("无效的 dynamic_id，跳过")
            return False

        dynamic_data = self._get_dynamic_detail(dynamic_id)
        if not dynamic_data:
            print("获取动态数据失败")
            return False

        try:
            processed_data = {
                "desc": {
                    "dynamic_id": int(dynamic_id),
                    "timestamp": dynamic_data["desc"]["timestamp"]
                },
                "card": dynamic_data["card"]
            }
            self.dynamic_processor.process_dynamic(processed_data, self.success_list, self.failed_list)
            return True
        except Exception as e:
            print(f"处理动态时发生错误: {e}")
            return False

    def run(self):
        print("\n开始重试未成功下载的URL...")
        unsaved_urls = self.file_manager.load_url_set(self.config.unsaved_url_filename)
        if not unsaved_urls:
            print("没有需要重试的URL")
            return
        print(f"发现 {len(unsaved_urls)} 条待重试URL")
        retry_queue = list(unsaved_urls)
        total_count = len(retry_queue)
        success_count = 0
        retry_limit = 2

        for attempt in range(retry_limit):
            print(f"\n第 {attempt+1} 次重试 (剩余 {len(retry_queue)} 条)")
            temp_failed = []
            for url in retry_queue:
                time.sleep(random.uniform(1.0, 2.0))
                if self._process_single_url(url):
                    success_count += 1
                    unsaved_urls.discard(url)
                else:
                    temp_failed.append(url)
            retry_queue = temp_failed
            if not retry_queue:
                break

        self.file_manager.write_url_file(self.config.unsaved_url_filename, list(unsaved_urls))
        print(f"\n{'='*30}")
        print(f"重试完成! 成功 {success_count}/{total_count} 条")
        if retry_queue:
            print(f"以下URL仍然失败:\n" + "\n".join(retry_queue))

class OperationMenu:
    def __init__(self, config, downloader):
        self.config = config
        self.downloader = downloader

    def run(self):
        while True:
            choice = input(
                "\n请选择操作:\n"
                "1. 开始新抓取\n"
                "2. 重试失败URL\n"
                "3. 退出\n"
                "4. 修改UID\n请输入数字: "
            ).strip()
            if choice == "1":
                method_choice = input(
                    "请选择保存方法:\n"
                    "1. 使用 date.log 截止日期停止，不检查 saved_url.txt\n"
                    "2. 检查 saved_url.txt，不使用 date.log 截止日期\n"
                    "请输入数字: "
                ).strip()
                if method_choice == "1":
                    method = 'date'
                elif method_choice == "2":
                    method = 'url'
                else:
                    print("无效选择，默认使用方法1")
                    method = 'date'
                
                for uid in self.config.uid_list:
                    print(f"\n开始下载UID: {uid}")
                    self.config.update_for_uid(uid)
                    file_manager = FileManager(self.config)
                    if method == 'date':
                        date_log_num = file_manager.read_date_log()
                    else:
                        date_log_num = file_manager.read_date_log()  # 方法2 只读第一行
                    saved_url_set = file_manager.load_url_set(self.config.saved_url_filename)
                    dynamic_processor = DynamicProcessor(self.config, file_manager, self.downloader, saved_url_set, date_log_num, method)
                    spider = BilibiliDynamicSpider(self.config, file_manager, dynamic_processor)
                    spider.run()
                    long_interval = 4.44
                    print("\n")
                    print("开始尖端科技之time.sleep", long_interval, "秒")
                    print("\n")
                    time.sleep(long_interval)
            elif choice == "2":
                for uid in self.config.uid_list:
                    print(f"\n重试UID: {uid} 的失败URL")
                    self.config.update_for_uid(uid)
                    file_manager = FileManager(self.config)
                    date_log_num = file_manager.read_date_log()
                    saved_url_set = file_manager.load_url_set(self.config.saved_url_filename)
                    dynamic_processor = DynamicProcessor(self.config, file_manager, self.downloader, saved_url_set, date_log_num, method='url')
                    retry = RetryFailedUrls(self.config, file_manager, dynamic_processor)
                    retry.run()
            elif choice == "3":
                print("程序退出")
                break
            elif choice == "4":
                self.change_uid()
            else:
                print("无效输入，请重新选择")

    def change_uid(self):
        new_uid_input = input("请输入新的UID（多个UID用逗号分隔）: ").strip()
        if new_uid_input:
            self.config.uid_list = [uid.strip() for uid in new_uid_input.split(',')]
            print(f"UID列表已更新为: {self.config.uid_list}")
        else:
            print("UID列表未更改")

def main():
    config = Config()
    downloader = Downloader(config)
    menu = OperationMenu(config, downloader)
    menu.run()

if __name__ == "__main__":
    main()
