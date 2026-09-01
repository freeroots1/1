import os
import requests

CACHE_DIR = r"E:\NRB\xiaozhi-esp32-server-main\main\xiaozhi-server\music"

class KugouMusic:
    SEARCH_API = "http://mobilecdn.kugou.com/api/v3/search/song"
    PLAY_API = "https://m.kugou.com/app/i/getSongInfo.php"

    @classmethod
    def search(cls, keyword, n=1):
        r = requests.get(
            cls.SEARCH_API,
            params={
                "format": "json",
                "keyword": keyword,
                "page": 1,
                "pagesize": 10,
                "showtype": 1
            },
            timeout=10
        )
        r.raise_for_status()
        return r.json()["data"]["info"][n - 1]

    @classmethod
    def get_mp3_url(cls, song):
        r = requests.get(
            cls.PLAY_API,
            params={"cmd": "playInfo", "hash": song["hash"]},
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        return data.get("url") or data.get("backup_url", [None])[0]

    @classmethod
    def download(cls, keyword):
        song = cls.search(keyword)
        url = cls.get_mp3_url(song)

        if not url:
            raise RuntimeError("未获取到 MP3 链接")

        os.makedirs(CACHE_DIR, exist_ok=True)

        filename = f"{song['songname']}.mp3"
        path = os.path.join(CACHE_DIR, filename)

        if os.path.exists(path):
            return path

        r = requests.get(url, timeout=15)
        with open(path, "wb") as f:
            f.write(r.content)

        return path
