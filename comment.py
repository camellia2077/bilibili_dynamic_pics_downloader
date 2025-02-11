import os
import re
import time
import requests

def download_images_with_cookie(oid, cookie, save_dir='images'):
    os.makedirs(save_dir, exist_ok=True)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://www.bilibili.com/opus/{oid}',
        'Cookie': cookie  # 关键身份参数
    }
    
    page = 1
    image_urls = set()  # 去重容器
    while True:
        api_url = f'https://api.bilibili.com/x/v2/reply/main?oid={oid}&type=17&next={page}'
        try:
            resp = requests.get(api_url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('code') != 0 or not data['data']['replies']:
                print('已到达最后一页或接口异常')
                break
                
            # 解析图片URL（正则匹配示例）
            pattern = re.compile(r'https?://i\d\.hdslb\.com/bfs/[^\s"]+\.(jpg|png|gif)')
            for reply in data['data']['replies']:
                urls = pattern.findall(reply['content']['message'])
                image_urls.update(urls)
                
                # 处理子评论
                if reply.get('replies'):
                    for sub_reply in reply['replies']:
                        sub_urls = pattern.findall(sub_reply['content']['message'])
                        image_urls.update(sub_urls)
            
            print(f'第 {page} 页解析完成，累计发现图片 {len(image_urls)} 张')
            page += 1
            time.sleep(1.5)  # 降低请求频率
            
        except Exception as e:
            print(f'请求失败: {str(e)}')
            break
    
    # 下载图片
    for idx, url in enumerate(image_urls):
        try:
            resp = requests.get(url, headers=headers, stream=True, timeout=15)
            if resp.status_code == 200:
                ext = url.split('.')[-1]
                with open(os.path.join(save_dir, f'image_{idx}.{ext}'), 'wb') as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                print(f'已下载: {url}')
        except Exception as e:
            print(f'下载失败 {url}: {str(e)}')

# 使用示例（替换为你的Cookie）
YOUR_COOKIE = "_uuid=FAA377D6-ED9F-310BC-519A-42C2B9B91062F10710infoc; buvid_fp=075b92ba210dd98d64009eaf6c2cbc64; buvid3=11EF371E-DBF9-D8D2-2B7D-5D0CE0A3AF4A22211infoc; b_nut=1732329713; header_theme_version=CLOSE; enable_web_push=DISABLE; match_float_version=ENABLE; DedeUserID=6967383; DedeUserID__ckMd5=9eb8b539885d768e; rpdid=|(u)YJJl~Rk~0J'u~JkJJJ)u~; buvid4=828502D2-463E-0EEA-9493-3B1F42F715AD66991-022073012-37bAVZ3%2FgV8gtfbxn3o9vQ%3D%3D; home_feed_column=4; fingerprint=075b92ba210dd98d64009eaf6c2cbc64; hit-dyn-v2=1; share_source_origin=COPY; CURRENT_QUALITY=80; enable_feed_channel=DISABLE; LIVE_BUVID=AUTO2617385612857275; PVID=1; browser_resolution=1111-511; CURRENT_FNVAL=4048; bp_t_offset_6967383=1032327322675445760; SESSDATA=e62d716a%2C1754799374%2Cfb6ef%2A22CjCkUNd-3W6Mwafpx0hT8bSxQ4qEGask7W3LrcDud4JAcdrC2w9WQNIxVWJBq178W04SVjdxQ0JyaDlGYmJmZ2ZMMGRmWGJ2VkMyNG1KN3hLc1U5MGlHTG9TVHdrT090c0FuQVpSQ01UQnZ1aTREY2JyQ0xRT2NYQ3BtSnhzUXB0cG5lNGM5ajhRIIEC; bili_jct=6e31b31455e4a586d6bf3af2edc8499a; sid=5h9f7jpl; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3Mzk1MTE5NTMsImlhdCI6MTczOTI1MjY5MywicGx0IjotMX0.fLrYQGoDaEVryYMUAyeKXrF88quIc3sa2qlWlZuLkxs; bili_ticket_expires=1739511893; b_lsid=9126CB86_194F38B4B3A; bsource=search_bing"
download_images_with_cookie('1030011609485934617', YOUR_COOKIE)