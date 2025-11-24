import os
import shutil
import requests
import time
import re
import threading
from Crypto.Cipher import AES
from urllib.parse import urljoin
import platform
'''

requests>=2.28.0
pycryptodome>=3.15.0
'''
system = platform.system().lower()
if system == 'windows':
    os.environ["PATH"] += os.pathsep + "./ffmpeg/win"

# !/usr/bin/env python3
import os
import subprocess
import tempfile
import shutil
from pathlib import Path


def merge_videos_with_filelist(file_list_path, output_path, max_files_per_batch=2):
    """
    使用文件列表合并视频（低内存优化版本）

    参数:
        file_list_path: 包含视频文件路径的文本文件
        output_path: 输出文件路径
        max_files_per_batch: 每批处理的文件数量（默认2个）
    """

    def read_file_list(file_path):
        """读取文件列表并返回视频文件路径列表"""
        video_files = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("file '"):
                        # 提取文件路径: 从 "file '/path/to/video.mp4'" 中提取路径
                        file_path = line[6:-1]  # 移除 "file '" 和结尾的 "'"
                        if os.path.exists(file_path):
                            video_files.append(file_path)
        except Exception as e:
            print(f"读取文件列表失败: {e}")
        return video_files

    def create_temp_file_list(files, suffix=""):
        """创建临时文件列表"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'{suffix}.txt') as f:
            for file_path in files:
                f.write(f"file '{os.path.abspath(file_path)}'\n")
        return f.name

    def merge_batch(video_files, batch_output_path):
        """合并一批视频文件"""
        batch_file_list = create_temp_file_list(video_files, "_batch")
        temp_files_to_clean = [batch_file_list]

        try:
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', batch_file_list,
                '-c', 'copy',
                '-threads', '1',
                '-max_muxing_queue_size', '512',
                '-y',
                batch_output_path
            ]

            print(f"正在合并 {len(video_files)} 个文件到: {batch_output_path}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return True
            else:
                print(f"合并失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("合并操作超时")
            return False
        except Exception as e:
            print(f"合并过程中发生错误: {e}")
            return False
        finally:
            # 清理临时文件
            for temp_file in temp_files_to_clean:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

    # 主逻辑开始
    print(f"开始处理文件列表: {file_list_path}")
    print(f"输出路径: {output_path}")
    print(f"每批处理文件数: {max_files_per_batch}")

    # 读取视频文件列表
    video_files = read_file_list(file_list_path)
    if not video_files:
        print("未找到有效的视频文件")
        return False

    print(f"找到 {len(video_files)} 个视频文件")

    # 如果文件数量少，直接合并
    if len(video_files) <= max_files_per_batch:
        return merge_batch(video_files, output_path)

    # 分片处理
    batches = []
    for i in range(0, len(video_files), max_files_per_batch):
        batch = video_files[i:i + max_files_per_batch]
        batches.append(batch)

    # 逐批合并
    temp_results = []
    for i, batch in enumerate(batches):
        temp_output = f"temp_batch_{i}.mp4"
        success = merge_batch(batch, temp_output)
        if success:
            temp_results.append(temp_output)
        else:
            print(f"批处理 {i} 失败")
            # 清理已生成的临时文件
            for temp_file in temp_results:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            return False

    # 合并所有临时文件
    if len(temp_results) > 1:
        final_file_list = create_temp_file_list(temp_results, "_final")
        final_success = merge_batch(temp_results, output_path)
        if os.path.exists(final_file_list):
            os.unlink(final_file_list)
    else:
        # 只有一个批次，直接重命名
        shutil.move(temp_results[0], output_path)
        final_success = True

    # 清理临时文件
    for temp_file in temp_results:
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    if final_success:
        print(f"视频合并完成: {output_path}")
    else:
        print("最终合并失败")

    return final_success





class M3U8Downloader:
    def __init__(self, headers=None):
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()

    def get(self, url):
        for _ in range(30):
            try:
                return self.session.get(url, headers=self.headers, timeout=60)
            except:
                time.sleep(1)

    def get_final_m3u8_url(self, first_url):
        """获取最终的m3u8文件地址"""
        response = self.get(first_url)
        content = response.text
        print(content)
        # 如果是多级m3u8，获取最终的m3u8地址
        if '#EXT-X-STREAM-INF' in content:
            lines = content.split('\n')
            for line in lines[::-1]:
                if '.m3u8' in line:
                    return urljoin(first_url, line)
        return first_url

    def parse_m3u8(self, m3u8_url):
        """解析m3u8文件，获取ts片段列表和密钥"""
        response = self.get(m3u8_url)
        content = response.text

        ts_list = []
        key_info = None
        base_url = m3u8_url.rsplit('/', 1)[0] + '/'

        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('#EXT-X-KEY'):
                # 解析加密信息
                method_match = re.search(r'METHOD=([^,]+)', line)
                uri_match = re.search(r'URI="([^"]+)"', line)
                if method_match and uri_match:
                    key_url = urljoin(base_url, uri_match.group(1))
                    key_response = self.get(key_url)
                    key_info = {
                        'method': method_match.group(1),
                        'key': key_response.content
                    }

            elif line.startswith('#EXTINF'):
                ts_url = lines[i + 1].strip()
                if not ts_url.startswith('http'):
                    ts_url = urljoin(base_url, ts_url)
                ts_list.append(ts_url)

        return ts_list, key_info, base_url

    def download_ts_segment(self, ts_url, file_path, key_info=None):
        """下载单个ts片段"""
        try:
            response = self.get(ts_url)
            content = response.content

            # 如果存在加密，进行解密
            if key_info and key_info['method'] == 'AES-128':
                cryptor = AES.new(key_info['key'], AES.MODE_CBC, key_info['key'])
                content = cryptor.decrypt(content)

            with open(file_path, 'wb') as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"下载失败 {ts_url}: {str(e)}")
            return False

    def multi_thread_download(self, ts_list, temp_dir, key_info=None, thread_num=10):
        """多线程下载所有ts片段"""
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        def download_task(ts_url, index):
            file_name = f"{index:05d}.ts"
            file_path = os.path.join(temp_dir, file_name)
            print("下载中：" , file_path)
            self.download_ts_segment(ts_url, file_path, key_info)

        threads = []
        for i, ts_url in enumerate(ts_list):
            thread = threading.Thread(target=download_task, args=(ts_url, i))
            threads.append(thread)
            thread.start()

            # 控制线程数量
            if len(threads) >= thread_num:
                for thread in threads:
                    thread.join()
                threads.clear()

        # 等待剩余线程完成
        for thread in threads:
            thread.join()

    def merge_ts_files(self, temp_dir, output_path):
        """合并ts文件为mp4"""
        ts_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.ts')])

        # 创建文件列表
        file_list_path = os.path.join(temp_dir, "filelist.txt")
        with open(file_list_path, 'w', encoding='utf-8') as f:
            for ts_file in ts_files:
                f.write(f"file '{ts_file}'\n")

        # 使用ffmpeg合并（需要提前安装ffmpeg并添加到环境变量）
        cmd = f'ffmpeg -f concat -safe 0 -i "{file_list_path}" -c copy "{output_path}"'
        result = os.system(cmd)
        os.remove(file_list_path)
        return result == 0

        # success = merge_videos_with_filelist(file_list_path , output_path)
        # os.remove(file_list_path)
        # return success

    def download_video(self, m3u8_url, output_dir, video_name, thread_num=10):
        """主下载方法"""
        print(f"开始下载: {video_name}")

        # 获取最终m3u8地址
        final_url = self.get_final_m3u8_url(m3u8_url)
        print(f"最终m3u8地址: {final_url}")

        # 解析m3u8文件
        ts_list, key_info, base_url = self.parse_m3u8(final_url)
        print(f"找到 {len(ts_list)} 个视频片段")

        # 创建临时目录
        temp_dir = os.path.join(output_dir, f"temp_{video_name}")

        # 多线程下载
        self.multi_thread_download(ts_list, temp_dir, key_info, thread_num)

        # 合并文件
        output_path = os.path.join(output_dir, f"{video_name}")
        success = self.merge_ts_files(temp_dir, output_path)

        # 清理临时文件
        shutil.rmtree(temp_dir)

        if success:
            print(f"下载完成: {output_path}")
        else:
            raise ValueError("合并文件失败")

        return success


if __name__ == "__main__":
    # 使用示例
    downloader = M3U8Downloader()

    # 替换为实际的m3u8地址
    m3u8_url = "https://example.com/index.m3u8"
    output_dir = "videos"
    video_name = "test_video"

    downloader.download_video(m3u8_url, output_dir, video_name)
