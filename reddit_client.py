import praw
from datetime import datetime, timezone


class RedditClient:
    def __init__(self, config):
        rc = config["reddit"]
        self.reddit = praw.Reddit(
            client_id=rc["client_id"],
            client_secret=rc["client_secret"],
            username=rc["username"],
            password=rc["password"],
            user_agent=rc["user_agent"],
        )
        self.username = rc["username"]

    def get_posts(self, subreddit, sort="hot", limit=25):
        sub = self.reddit.subreddit(subreddit)
        if sort == "new":
            return list(sub.new(limit=limit))
        elif sort == "rising":
            return list(sub.rising(limit=limit))
        elif sort == "top":
            return list(sub.top(limit=limit, time_filter="day"))
        else:
            return list(sub.hot(limit=limit))

    def has_commented_on(self, post_id):
        submission = self.reddit.submission(id=post_id)
        submission.comments.replace_more(limit=0)
        for comment in submission.comments.list():
            if comment.author and comment.author.name == self.username:
                return True
        return False

    def get_top_comments(self, post_id, limit=10):
        submission = self.reddit.submission(id=post_id)
        submission.comments.replace_more(limit=0)
        comments = []
        for c in submission.comments[:limit]:
            if c.body and c.body != "[deleted]":
                comments.append(c.body)
        return comments

    def post_comment(self, post_id, body):
        submission = self.reddit.submission(id=post_id)
        comment = submission.reply(body)
        return comment.id

    def create_post(self, subreddit, title, body):
        sub = self.reddit.subreddit(subreddit)
        submission = sub.submit(title, selftext=body)
        return submission.id

    def get_my_karma(self):
        me = self.reddit.user.me()
        return {
            "comment_karma": me.comment_karma,
            "link_karma": me.link_karma,
            "total": me.comment_karma + me.link_karma,
        }

    def get_my_recent_comments(self, limit=20):
        me = self.reddit.user.me()
        results = []
        for c in me.comments.new(limit=limit):
            results.append({
                "id": c.id,
                "subreddit": str(c.subreddit),
                "body": c.body[:100],
                "score": c.score,
                "created_utc": datetime.fromtimestamp(c.created_utc, tz=timezone.utc).isoformat(),
                "permalink": c.permalink,
            })
        return results

    def get_comment_score(self, comment_id):
        comment = self.reddit.comment(id=comment_id)
        return comment.score

    def get_post_score(self, post_id):
        submission = self.reddit.submission(id=post_id)
        return submission.score
