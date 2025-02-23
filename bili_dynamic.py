import os
import re
import json
import time
import requests
import datetime
import random
#2025 2 6
FILE_NAME_MAX_LENGTH = 25
COOKIE = ""
DELAY_FIRST = 0.5
DELAY_LAST = 0.6

# 文件夹命名的时候，内容合并连续空格

# =======================
# 配置类:获取用户输入,保存基本配置信息
# =======================
class Config:

    def __init__(self, download_dir=None, uid=None, interval=None):
        self.COOKIE = COOKIE
        self.download_dir = download_dir or self.get_download_dir()
        self.uid = uid or self.get_uid()
        self.interval = interval or self.get_interval()
        #在目录self.download_dir下创建saved_url.txt和unsaved_url.txt
        self.saved_url_filename = os.path.join(self.download_dir, "saved_url.txt")
        self.unsaved_url_filename = os.path.join(self.download_dir, "unsaved_url.txt")
        # 确保下载目录存在
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    def get_download_dir(self):
        download_dir = input("请输入下载目录(默认为 C:\Base1\\bbb\\bili):").strip()
        return download_dir if download_dir else r"C:\Base1\bbb\bili"

    def get_uid(self):
        uid = input("请输入bilibili用户uid(默认为坂坂白 560647)Kitaro绮太郎2075682:").strip()
        return uid if uid else "560647"

    def get_interval(self):
        interval = input("请输入下载间隔(秒,默认为3):").strip()
        try:
            return float(interval) if interval else 3
        except Exception:
            return 3

# =======================
# 文件操作类:处理文件的读写、存在性检查等
# =======================
class FileManager:
    def __init__(self, config: Config):
        self.config = config
        self.ensure_file_exists(self.config.saved_url_filename)
        self.ensure_file_exists(self.config.unsaved_url_filename)

    def ensure_file_exists(self, filename):
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                pass

    def load_url_set(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return {line.strip() for line in f if line.strip()}
        else:
            return set()

    def write_url_file(self, filename, urls):
        """覆盖写入 URL 文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url + "\n")

    def append_url_file(self, filename, urls):
        """追加写入 URL 文件"""
        with open(filename, 'a', encoding='utf-8') as f:
            for url in urls:
                f.write(url + "\n")

# =======================
# 工具类:提供公共工具方法
# =======================
class Utils:
    #非法字符
    ILLEGAL_CHAR_PATTERN = r'[#@.<>:"/\\|?*\n\r]'
    @staticmethod
    #FILE_NAME_MAX_LENGTH = 40
    def sanitize_filename(name, FILE_NAME_MAX_LENGTH):
        # 去除非法字符
        name = re.sub(Utils.ILLEGAL_CHAR_PATTERN, '', name)
        # 这个方法会移除字符串开头和结尾处的所有空白字符（例如空格、制表符、换行符等）。
        # 合并连续空格
        name = re.sub(r'\s+', ' ', name)
        # 去除首尾空白和句点
        name = name.strip(" .")

        # 截断前再次检查长度（防止截断后残留非法后缀）
        if len(name) > FILE_NAME_MAX_LENGTH:
            name = name[:FILE_NAME_MAX_LENGTH].rstrip(" .")  # 截断后再次去除末尾非法字符
        return name
    
    @staticmethod
    def parse_dynamic_card(card_str):
        try:
            card_dict = json.loads(card_str)
            return card_dict
        except Exception as e:
            print("解析 card 失败:", e)
            return {}

    @staticmethod
    def format_datetime(timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp)
        # 月份、日期不带前导零
        return f"{dt.year}-{dt.month}-{dt.day}-{dt.hour:02d}:{dt.minute:02d}"

# =======================
# 下载类:负责文件下载(例如图片下载)
# =======================
class Downloader:
    def __init__(self, config: Config):
        self.config = config
        self.headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/90.0.4430.93 Safari/537.36"),
            "Cookie": config.COOKIE
        }

    def download_file(self, url, filepath):
        try:
            random_number = random.uniform(DELAY_FIRST,DELAY_LAST)
            time.sleep(random_number)#延迟
            r = requests.get(url, headers=self.headers, stream=True, timeout=10)
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                print(f"保存文件:{filepath}")
            else:
                print(f"下载失败 {url} 状态码:{r.status_code}")
        except Exception as e:
            print(f"下载 {url} 出错:{e}")

# =======================
# 动态处理类:处理单条动态,生成文件夹、info.txt,并下载图片
# =======================
class DynamicProcessor:
    def __init__(self, config: Config, file_manager: FileManager, downloader: Downloader):
        self.config = config
        self.file_manager = file_manager
        self.downloader = downloader

    def process_dynamic(self, dynamic, saved_url_set, success_list, failed_list):
        dynamic_url = None
        try:
            random_number = random.uniform(DELAY_FIRST, DELAY_LAST)
            time.sleep(random_number)
            desc = dynamic.get("desc", {})
            dynamic_id = desc.get("dynamic_id")
            if not dynamic_id:
                print("无法获取 dynamic_id,跳过该动态")
                return
            dynamic_id = str(dynamic_id)  # 确保 dynamic_id 是字符串
            dynamic_url = f"https://t.bilibili.com/{dynamic_id}"
            if dynamic_url in saved_url_set:
                print(f"动态 {dynamic_url} 已下载,跳过。")
                return

            # 发布时间
            timestamp = desc.get("timestamp")
            time_str = Utils.format_datetime(timestamp) if timestamp else "未知时间"

            # 解析动态详情
            card_str = dynamic.get("card", "")
            card_dict = Utils.parse_dynamic_card(card_str)

            # 获取动态内容:优先取 description,再取 content
            dynamic_content = ""
            if "item" in card_dict:
                item = card_dict["item"]
                if "description" in item:
                    dynamic_content = item["description"]
                elif "content" in item:
                    dynamic_content = item["content"]

            # 判断动态是否有内容(去除空白字符后是否为空)
            has_content = bool(dynamic_content.strip())
            if has_content:
                #全局变量file_name_max_length控制长度
                content_clean = Utils.sanitize_filename(dynamic_content, FILE_NAME_MAX_LENGTH)
                # 用短横线替换空格，避免末尾出现多余空白
                folder_name = f"{time_str}-{content_clean}".replace(" ", "-")
                folder_name = Utils.sanitize_filename(folder_name,FILE_NAME_MAX_LENGTH)
                dynamic_folder = os.path.join(self.config.download_dir, folder_name)
            else:
                # 如果动态内容为空,则放在 download_dir/null 下,以 dynamic_id 命名子文件夹
                null_folder = os.path.join(self.config.download_dir, "null")
                if not os.path.exists(null_folder):
                    os.makedirs(null_folder)
                    print(f"创建空内容动态存放文件夹: {null_folder}")
                dynamic_folder = os.path.join(null_folder, dynamic_id)

            if not os.path.isdir(dynamic_folder):
                if os.path.exists(dynamic_folder):
                    print(f"路径 {dynamic_folder} 存在但不是目录，请检查！")
                    os.remove(dynamic_folder)
                os.makedirs(dynamic_folder)
                print(f"创建文件夹: {dynamic_folder}")
            else:
                print(f"文件夹已存在: {dynamic_folder}")

            # 生成 info.txt,包含 URL、发布时间和完整内容
            info_path = os.path.join(dynamic_folder, "info.txt")
            with open(info_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {dynamic_url}\n")
                f.write(f"发布时间: {time_str}\n")
                f.write("内容:\n")
                f.write(dynamic_content)
            print(f"保存动态信息到: {info_path}")

            # 下载图片(如果有)
            pics = []
            if "item" in card_dict and "pictures" in card_dict["item"]:
                pics = card_dict["item"]["pictures"]
            if pics:
                for idx, pic in enumerate(pics, start=1):
                    img_url = pic.get("img_src")
                    if not img_url:
                        continue
                    ext = os.path.splitext(img_url)[1]
                    if not ext:
                        ext = ".jpg"
                    img_filename = f"{idx}{ext}"
                    img_path = os.path.join(dynamic_folder, img_filename)
                    print(f"下载图片: {img_url}")
                    self.downloader.download_file(img_url, img_path)
            else:
                print("该动态没有图片。")

            # 记录处理成功
            saved_url_set.add(dynamic_url)
            success_list.append(dynamic_url)
        except Exception as e:
            print("处理动态出错:", e)
            if dynamic_url:
                failed_list.append(dynamic_url)

# =======================
# 主爬虫类:分页获取动态数据,并调用 DynamicProcessor 处理每条动态
# =======================
class BilibiliDynamicSpider:
    def __init__(self, config: Config, file_manager: FileManager, dynamic_processor: DynamicProcessor):
        self.config = config
        self.file_manager = file_manager
        self.dynamic_processor = dynamic_processor
        self.saved_url_set = self.file_manager.load_url_set(self.config.saved_url_filename)
        self.success_list = []
        self.failed_list = []

    def run(self):
        #api接口
        base_url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history"
        params = {"host_uid": self.config.uid, "offset_dynamic_id": 0}
        has_more = True
        page_count = 1

        while has_more:
            print(f"正在处理第 {page_count} 页动态...")
            try:
                response = requests.get(base_url, headers=self.dynamic_processor.downloader.headers, params=params, timeout=10)
                if response.status_code != 200:
                    print("请求失败,状态码:", response.status_code)
                data = response.json()
                if data.get("code") != 0:
                    message = data.get("message", "")
                    print("接口返回错误信息:", message)
                    # 若提示登录相关信息，则提示cookie错误
                    if "请登录" in message or "cookie" in message.lower():
                        print("请在程序输入正确的cookie")
                    break
                data_data = data.get("data", {})
                cards = data_data.get("cards", [])
                has_more = data_data.get("has_more", False)
                if "next_offset" in data_data:
                    params["offset_dynamic_id"] = data_data["next_offset"]
                else:
                    if cards:
                        last_card = cards[-1]
                        last_desc = last_card.get("desc", {})
                        params["offset_dynamic_id"] = last_desc.get("dynamic_id", 0)
                    else:
                        has_more = False

                if not cards:
                    print("当前页没有动态数据,结束下载。")
                    break

                for dynamic in cards:
                    self.dynamic_processor.process_dynamic(dynamic, self.saved_url_set, self.success_list, self.failed_list)

                page_count += 1
                print(f"等待 {self.config.interval} 秒后继续下载下一页...")
                time.sleep(self.config.interval)
            except Exception as e:
                print("处理页面时发生错误:", e)
                break

        # ================= 关键修改部分开始 =================
        # 加载已存在的未保存URL（保留历史记录）
        existing_unsaved = self.file_manager.load_url_set(self.config.unsaved_url_filename)
        # 合并所有失败URL（新旧结合）
        all_failed_urls = existing_unsaved.union(set(self.failed_list))
        # 移除已成功的URL（即使之前失败过）
        all_failed_urls -= set(self.success_list)
        # 覆盖写入未保存URL文件
        self.file_manager.write_url_file(
            self.config.unsaved_url_filename, 
            list(all_failed_urls)  # 转换为列表
        )
        # 追加成功URL到已保存文件
        if self.success_list:
            self.file_manager.append_url_file(
                self.config.saved_url_filename, 
                self.success_list
            )
        # ================= 关键修改部分结束 =================

# =======================
# 新增重试失败URL的类
# =======================
class RetryFailedUrls:
    def __init__(self, config: Config, file_manager: FileManager, dynamic_processor: DynamicProcessor):
        self.config = config
        self.file_manager = file_manager
        self.dynamic_processor = dynamic_processor
        self.saved_url_set = self.file_manager.load_url_set(self.config.saved_url_filename)
        self.success_list = []
        self.failed_list = []
        # 新增API请求头
        self.headers = {
            **dynamic_processor.downloader.headers,
            "Referer": "https://t.bilibili.com/"
        }

    def _get_dynamic_detail(self, dynamic_id):
        """通过动态ID获取完整动态数据"""
        api_url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail"
        params = {"dynamic_id": dynamic_id}
        
        try:
            response = requests.get(
                api_url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            if response.status_code != 200:
                print(f"请求失败 状态码:{response.status_code}")
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
        """处理单个URL的全流程"""
        print(f"\n{'='*30}\n正在处理URL: {url}")
        
        # 解析 dynamic_id
        if not url.startswith("https://t.bilibili.com/"):
            print("非标准动态URL，跳过")
            return False
            
        dynamic_id = url.split("/")[-1]
        if not dynamic_id.isdigit():
            print("无效的 dynamic_id，跳过")
            return False

        # 获取完整动态数据
        dynamic_data = self._get_dynamic_detail(dynamic_id)
        if not dynamic_data:
            print("获取动态数据失败")
            return False

        # 构造标准数据结构
        try:
            processed_data = {
                "desc": {
                    "dynamic_id": int(dynamic_id),
                    "timestamp": dynamic_data["desc"]["timestamp"]
                },
                "card": dynamic_data["card"]
            }
        except KeyError as e:
            print(f"动态数据结构异常: {str(e)}字段缺失")
            return False

        # 调用原有处理逻辑
        try:
            self.dynamic_processor.process_dynamic(
                processed_data,
                self.saved_url_set,
                self.success_list,
                self.failed_list
            )
            return True
        except Exception as e:
            print(f"处理动态时发生错误: {e}")
            return False

    def run(self):
        """执行重试操作"""
        print("\n开始重试未成功下载的URL...")

        # 加载待处理URL，并确保其为 set 类型（方便后续删除）
        unsaved_urls = self.file_manager.load_url_set(self.config.unsaved_url_filename)
        if not unsaved_urls:
            print("没有需要重试的URL")
            return

        # 如果加载的不是 set，可以手动转换：unsaved_urls = set(unsaved_urls)
        unsaved_urls = set(unsaved_urls)
        
        print(f"发现{len(unsaved_urls)}条待重试URL")
        
        retry_queue = list(unsaved_urls)
        total_count = len(retry_queue)
        success_count = 0
        retry_limit = 2  # 最大重试次数

        for attempt in range(retry_limit):
            print(f"\n第{attempt+1}次重试 (剩余{len(retry_queue)}条)")
            temp_failed = []
            
            for url in retry_queue:
                # 随机延迟防止被封
                time.sleep(random.uniform(1.0, 2.0))
                
                if self._process_single_url(url):
                    success_count += 1
                    # 如果当前 URL 处理成功，则从 unsaved_urls 中移除
                    unsaved_urls.discard(url)
                else:
                    temp_failed.append(url)
                    
            retry_queue = temp_failed
            if not retry_queue:
                break

        # 将成功重试的 URL 追加到已保存的文件
        if self.success_list:
            self.file_manager.append_url_file(self.config.saved_url_filename, self.success_list)
        # 将剩下的失败 URL 写回 unsaved_url.txt（覆盖原文件）
        self.file_manager.write_url_file(self.config.unsaved_url_filename, list(unsaved_urls))
        
        print(f"\n{'='*30}")
        print(f"重试完成! 成功{success_count}/{total_count}条")
        if retry_queue:
            print(f"以下URL仍然失败:\n" + "\n".join(retry_queue))
#操作菜单
class OperationMenu:
    def __init__(self, config, file_manager, dynamic_processor):
        """
        初始化时传入所需的对象：
          - config：配置对象
          - file_manager：文件操作对象
          - dynamic_processor：动态处理对象
        """
        self.config = config
        self.file_manager = file_manager
        self.dynamic_processor = dynamic_processor

    def run(self):
        while True:
            choice = input(
                "\n请选择操作:\n"
                "1. 开始新抓取\n"
                "2. 重试失败URL\n"
                "3. 退出\n请输入数字: "
            ).strip()

            if choice == "1":
                spider = BilibiliDynamicSpider(self.config, self.file_manager, self.dynamic_processor)
                spider.run()
            elif choice == "2":
                retry = RetryFailedUrls(self.config, self.file_manager, self.dynamic_processor)
                retry.run()
            elif choice == "3":
                print("程序退出")
                break
            else:
                print("无效输入，请重新选择")

# 主函数
def main():
    # 初始化配置
    config = Config()
    file_manager = FileManager(config)
    downloader = Downloader(config)
    dynamic_processor = DynamicProcessor(config, file_manager, downloader)

    menu = OperationMenu(config, file_manager, dynamic_processor)
    menu.run()
if __name__ == "__main__":
    main()
