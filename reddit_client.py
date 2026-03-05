import time
import requests
from datetime import datetime, timezone


class RedditClient:
    BASE = "https://old.reddit.com"

    def __init__(self, config):
        rc = config["reddit"]
        self.username = rc.get("username", "")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": rc.get("user_agent", "linux:redditcreator:v0.1"),
        })

        if rc.get("reddit_session"):
            # Cookie-based auth (Google auth users etc.)
            self.session.cookies.set("reddit_session", rc["reddit_session"], domain=".reddit.com")
            # Fetch modhash and username from /api/me
            me = self._get_json("/api/me")
            self.username = me.get("data", {}).get("name", self.username)
            self.modhash = me.get("data", {}).get("modhash", "")
        elif rc.get("password"):
            # Username/password login
            resp = self.session.post(f"{self.BASE}/api/login/{self.username}", data={
                "user": self.username,
                "passwd": rc["password"],
                "api_type": "json",
            })
            resp.raise_for_status()
            login_data = resp.json()
            errors = login_data.get("json", {}).get("errors", [])
            if errors:
                raise Exception(f"Reddit login failed: {errors}")
            self.modhash = login_data["json"]["data"]["modhash"]
            time.sleep(2)
        else:
            raise Exception("Config needs either 'reddit_session' or 'username'+'password'")

    def _get_json(self, path, params=None):
        url = f"{self.BASE}{path}.json"
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post_api(self, endpoint, data):
        data["uh"] = self.modhash
        resp = self.session.post(f"{self.BASE}/api/{endpoint}", data=data)
        resp.raise_for_status()
        return resp.json()

    def get_posts(self, subreddit, sort="hot", limit=25):
        data = self._get_json(f"/r/{subreddit}/{sort}", params={"limit": limit})
        posts = []
        for child in data.get("data", {}).get("children", []):
            posts.append(Post(child["data"]))
        return posts

    def has_commented_on(self, post_id):
        data = self._get_json(f"/comments/{post_id}", params={"limit": 500})
        if len(data) < 2:
            return False
        comments = data[1].get("data", {}).get("children", [])
        for c in comments:
            author = c.get("data", {}).get("author")
            if author == self.username:
                return True
        return False

    def get_top_comments(self, post_id, limit=10):
        data = self._get_json(f"/comments/{post_id}", params={"limit": limit, "sort": "top"})
        comments = []
        if len(data) >= 2:
            for c in data[1].get("data", {}).get("children", []):
                body = c.get("data", {}).get("body", "")
                if body and body != "[deleted]":
                    comments.append(body)
        return comments[:limit]

    def post_comment(self, post_id, body):
        result = self._post_api("comment", {
            "thing_id": f"t3_{post_id}",
            "text": body,
        })
        # Extract comment id from response
        things = result.get("jquery", [])
        for item in things:
            if isinstance(item, list) and len(item) >= 4:
                inner = item[3]
                if isinstance(inner, list):
                    for obj in inner:
                        if isinstance(obj, dict) and "data" in obj:
                            cdata = obj["data"]
                            if "things" in cdata:
                                for thing in cdata["things"]:
                                    if thing.get("kind") == "t1":
                                        return thing["data"]["id"]
        # Fallback: try to get from json response
        comment_data = result.get("json", {}).get("data", {}).get("things", [])
        if comment_data:
            return comment_data[0].get("data", {}).get("id")
        return None

    def create_post(self, subreddit, title, body):
        result = self._post_api("submit", {
            "sr": subreddit,
            "kind": "self",
            "title": title,
            "text": body,
            "sendreplies": "true",
        })
        post_url = result.get("json", {}).get("data", {}).get("url", "")
        post_id = result.get("json", {}).get("data", {}).get("id")
        return post_id

    def get_my_karma(self):
        data = self._get_json(f"/user/{self.username}/about")
        user_data = data.get("data", {})
        ck = user_data.get("comment_karma", 0)
        lk = user_data.get("link_karma", 0)
        return {
            "comment_karma": ck,
            "link_karma": lk,
            "total": ck + lk,
        }

    def get_my_recent_comments(self, limit=20):
        data = self._get_json(f"/user/{self.username}/comments", params={"limit": limit})
        results = []
        for child in data.get("data", {}).get("children", []):
            c = child["data"]
            results.append({
                "id": c.get("id"),
                "subreddit": c.get("subreddit"),
                "body": c.get("body", "")[:100],
                "score": c.get("score", 0),
                "created_utc": datetime.fromtimestamp(c.get("created_utc", 0), tz=timezone.utc).isoformat(),
                "permalink": c.get("permalink", ""),
            })
        return results

    def get_comment_score(self, comment_id):
        data = self._get_json(f"/api/info", params={"id": f"t1_{comment_id}"})
        children = data.get("data", {}).get("children", [])
        if children:
            return children[0].get("data", {}).get("score", 0)
        return 0

    def get_post_score(self, post_id):
        data = self._get_json(f"/api/info", params={"id": f"t3_{post_id}"})
        children = data.get("data", {}).get("children", [])
        if children:
            return children[0].get("data", {}).get("score", 0)
        return 0


class Post:
    """Lightweight post object matching the interface scout.py expects."""
    def __init__(self, data):
        self.id = data.get("id", "")
        self.title = data.get("title", "")
        self.selftext = data.get("selftext", "")
        self.score = data.get("score", 0)
        self.num_comments = data.get("num_comments", 0)
        self.created_utc = data.get("created_utc", 0)
        self.permalink = data.get("permalink", "")
        self.stickied = data.get("stickied", False)
        self.locked = data.get("locked", False)
