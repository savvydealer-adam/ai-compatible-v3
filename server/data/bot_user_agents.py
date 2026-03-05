"""AI bot user agent strings for access testing."""

# v2 original 8 bots
AI_BOTS: dict[str, str] = {
    "GPTBot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko;"
        " compatible; GPTBot/1.2; +https://openai.com/gptbot)"
    ),
    "ChatGPT-User": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko;"
        " compatible; ChatGPT-User/1.0; +https://openai.com/bot)"
    ),
    "Claude-Web": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko;"
        " compatible; Claude-Web/1.0; +https://www.anthropic.com/claude-web)"
    ),
    "Google-Extended": (
        "Mozilla/5.0 (compatible; Google-Extended/1.0;"
        " +https://developers.google.com/search/docs/"
        "crawling-indexing/google-extended)"
    ),
    "PerplexityBot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko;"
        " compatible; PerplexityBot/1.0;"
        " +https://perplexity.ai/perplexitybot)"
    ),
    "CCBot": "CCBot/2.0 (https://commoncrawl.org/faq/)",
    "Bytespider": ("Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)"),
    "Amazonbot": (
        "Mozilla/5.0 (compatible; Amazonbot/0.1; +https://developer.amazon.com/support/amazonbot)"
    ),
}

# v3 new bots (9 additional)
AI_BOTS_V3: dict[str, str] = {
    "OAI-SearchBot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko;"
        " compatible; OAI-SearchBot/1.0;"
        " +https://openai.com/searchbot)"
    ),
    "Claude-SearchBot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko;"
        " compatible; ClaudeBot/1.0;"
        " +https://www.anthropic.com/claude-bot)"
    ),
    "Claude-User": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko;"
        " compatible; Claude-User/1.0;"
        " +https://www.anthropic.com/claude-user)"
    ),
    "Meta-ExternalAgent": (
        "Mozilla/5.0 (compatible; Meta-ExternalAgent/1.0;"
        " +https://developers.facebook.com/docs/sharing/bot/)"
    ),
    "Meta-WebIndexer": (
        "Mozilla/5.0 (compatible; Meta-WebIndexer/1.0;"
        " +https://developers.facebook.com/docs/sharing/webindexer/)"
    ),
    "Applebot-Extended": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5)"
        " AppleWebKit/605.1.15 (KHTML, like Gecko)"
        " Version/13.1.1 Safari/605.1.15"
        " (Applebot-Extended/0.1;"
        " +http://www.apple.com/go/applebot)"
    ),
    "DuckAssistBot": (
        "Mozilla/5.0 (compatible; DuckAssistBot/1.0; +https://duckduckgo.com/duckassistbot)"
    ),
    "MistralAI-User": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; MistralAI-User/1.0)"
    ),
    "Gemini-Deep-Research": (
        "Mozilla/5.0 (compatible; Google-Extended/1.0;"
        " +https://developers.google.com/search/docs/"
        "crawling-indexing/google-extended) Gemini-Deep-Research"
    ),
}

# Combined for v3
ALL_AI_BOTS: dict[str, str] = {**AI_BOTS, **AI_BOTS_V3}

# Key bots for scoring (original 5 used in v2 blocking score)
KEY_AI_BOTS = [
    "GPTBot",
    "Claude-Web",
    "PerplexityBot",
    "Google-Extended",
    "CCBot",
]

# Vehicle schema types for counting
VEHICLE_SCHEMA_TYPES = [
    "Vehicle",
    "Car",
    "Motorcycle",
    "BusOrCoach",
    "MotorizedBicycle",
    "Product",
    "IndividualProduct",
]

# OpenAI bots that use ChatGPT IP whitelist with Cloudflare
OPENAI_BOTS = {"GPTBot", "ChatGPT-User", "OAI-SearchBot"}

# ChatGPT IP ranges whitelisted by Cloudflare
CHATGPT_IP_CIDRS = [
    "23.102.140.0/24",
    "40.84.180.224/28",
    "52.230.152.0/24",
    "52.233.106.0/24",
    "104.209.37.0/24",
    "13.66.11.96/28",
    "40.84.180.64/28",
    "23.98.142.176/28",
    "40.84.180.192/28",
    "52.156.197.208/28",
    "20.97.189.0/24",
    "20.14.0.0/23",
    "52.225.75.208/28",
    "52.232.234.0/24",
    "40.84.180.128/28",
    "20.171.207.0/24",
    "20.15.240.64/28",
    "20.206.229.224/28",
    "20.161.75.208/28",
    "20.171.206.0/23",
    "4.227.2.0/24",
]
