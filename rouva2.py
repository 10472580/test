import os
import hashlib
from utils.AESCBCPKCS7 import AESCBCPKCS7
from utils.M3U8Downloader import M3U8Downloader
from utils.PasswordZip import PasswordZip
from utils.aliyun import upload_aliyun,set_token

os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"

import requests
from lxml import etree

headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}


def download(url, file_name):
    print(url, file_name)
    md5 = hashlib.md5(url.encode()).hexdigest()
    if is_finish(md5):
        return


    m3u8_url = requests.get("https://rouva2.xyz/api/v/" + url.split('/')[-1], headers=headers).json()['video']["videoUrl"]
    # m3u8_url = requests.get(videoUrl, headers=headers).text.split("\n")[-1] # m3u8清晰度
    # print(m3u8_url)

    # response = requests.get(url, headers=headers).text
    # html = etree.HTML(response)
    # m3u8_url = html.xpath("//video[@id='video-play']/@data-src")[0]

    folder_path = "downloads/" + md5
    os.makedirs(folder_path, exist_ok=True)

    M3U8Downloader().download_video(m3u8_url, folder_path, "1.mp4")

    with open(folder_path + "/0", "w+") as f:
        f.write(ase.encrypt(file_name))

    zip_name = folder_path + ".zip"
    pzip.compress(
        source=folder_path,
        zip_filename=zip_name,
        include_parent_dir=True,
        compress_level=6,
        delete_srouce=True
    )

    if upload_aliyun(zip_name , "韦小宝"):
        is_finish(md5, False)
    os.remove(zip_name)


def is_finish(md5, query_flag=True , token = False):
    # rdesktop -g 1024x768 -a 16 -u administrator -0 8.138.199.217:3389
    url = "http://8.138.199.217:8882/api/"
    if token:
        return set_token(requests.get(url + "token").text)
    # path = "http://127.0.0.1:5000/api/md5/{}?md5=" + md5
    path = url + "md5/{}?md5=" + md5
    if query_flag:
        return requests.get(path.format("query")).text == "true"
    return requests.get(path.format("add"))


def get_page():
    page = 0
    while True:
        page += 1
        url = "https://rouva2.xyz/search?q=91%E5%A4%A7%E7%A5%9E+%E9%9F%8B%E5%B0%8F%E5%AF%B6&t=&sort=&page=" + str(page)
        response = requests.get(url, headers=headers).text
        html = etree.HTML(response)
        videos = html.xpath('//div[@class="aspect-video relative"]/a')
        if len(videos) == 0:
            break
        for video in videos:
            download(video.attrib['href'], video.xpath('./img[@class="relative w-full h-full object-contain"]/@alt')[0])


if __name__ == '__main__':
    ase = AESCBCPKCS7()
    pzip = PasswordZip(password="lfj-666-888-lfj")
    is_finish(None , token = True)
    get_page()
