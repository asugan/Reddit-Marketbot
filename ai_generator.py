import random
from openai import OpenAI


def create_client(config):
    ai = config["ai"]
    return OpenAI(
        base_url=ai["base_url"],
        api_key=ai["api_key"],
        timeout=ai.get("request_timeout", 60),
    )


def generate_comment(client, model, post_item, persona, existing_comments=None):
    length_style = random.choice([
        "Write a short response (1-3 sentences).",
        "Write a medium-length response (3-5 sentences).",
        "Write a longer, more detailed response (5-8 sentences).",
    ])

    existing_str = ""
    if existing_comments:
        existing_str = "\n\nExisting comments on this post (do NOT repeat these ideas):\n" + "\n---\n".join(existing_comments[:5])

    prompt = f"""{persona}

You are commenting on a Reddit post in r/{post_item['subreddit']}.

Post title: {post_item['target_post_title']}
Post body: {post_item.get('target_post_body', '') or '(no body)'}
{existing_str}

{length_style}

Rules:
- Write as a real person, not an AI
- Do NOT start with "Great question!", "That's a great point!", or similar
- Do NOT use bullet points or numbered lists unless truly natural
- Do NOT say "As an AI" or "I'm an AI" or anything similar
- Vary your tone naturally - sometimes casual, sometimes more thoughtful
- You can disagree, share personal anecdotes (make them up if needed), or ask follow-up questions
- Use Reddit-appropriate language and tone
- Do NOT use markdown headers
- Occasionally use lowercase or informal punctuation for authenticity"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=random.uniform(0.7, 1.0),
        max_tokens=500,
    )

    return response.choices[0].message.content.strip()


def generate_post(client, model, subreddit, persona, topic_hints=None):
    hints_str = ""
    if topic_hints:
        hints_str = f"\nTopic suggestions: {', '.join(topic_hints)}"

    prompt = f"""{persona}

Create a Reddit post for r/{subreddit}.
{hints_str}

Generate both a title and body text.

Rules:
- Title should be engaging but not clickbait
- Body should be natural, conversational
- Do NOT write like an AI - no bullet lists, no "As an AI"
- Write as a regular community member
- Can be a question, discussion, experience sharing, or opinion

Format your response as:
TITLE: <your title here>
BODY: <your body text here>"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=random.uniform(0.7, 1.0),
        max_tokens=800,
    )

    text = response.choices[0].message.content.strip()

    title = ""
    body = ""

    if "TITLE:" in text and "BODY:" in text:
        title = text.split("TITLE:", 1)[1].split("BODY:", 1)[0].strip()
        body = text.split("BODY:", 1)[1].strip()
    else:
        lines = text.split("\n", 1)
        title = lines[0][:200]
        body = lines[1].strip() if len(lines) > 1 else ""

    return title, body
