# DeepSearch Workflow Mock Data
DEEPSEARCH_ISSUE = {
    "description": "The assistant fails to search the internet to retrieve documentation",
    "examples": [
        # Positive examples (MATCH) - Assistant fails to access docs
        {
            "user": "What's the correct kubectl command to stream logs from a Kubernetes pod, and can I use a wildcard in place of pod?",
            "assistant": "Sorry, I was unable to search for Kubernetes reference.",
            "user_label": "MATCH",
        },
        {
            "user": "How do I configure GitHub Actions to skip caching for a specific job?",
            "assistant": "I cannot reach the GitHub Actions documentation.",
            "user_label": "MATCH",
        },
        {
            "user": "What are the Docker Compose environment variable syntax options?",
            "assistant": "I'm unable to access the Docker documentation at this time.",
            "user_label": "MATCH",
        },
        {
            "user": "Can you show me the AWS CLI command to list all S3 buckets?",
            "assistant": "Sorry, I failed to retrieve the AWS documentation.",
            "user_label": "MATCH",
        },
        {
            "user": "What's the PostgreSQL query to find duplicate rows?",
            "assistant": "I cannot access the PostgreSQL documentation.",
            "user_label": "MATCH",
        },
        {
            "user": "How do I set up authentication in Next.js?",
            "assistant": "I was unable to search for Next.js documentation.",
            "user_label": "MATCH",
        },
        # Negative examples (NO_MATCH) - User having trouble, not assistant
        {
            "user": "What's the correct kubectl command to stream logs from a Cron Job *run*, not the cron job template itself?",
            "assistant": "Sorry I was unable to search for the kubernetes reference",
            "user_label": "NO_MATCH",  # User marked as NO_MATCH - user is asking, not assistant failing
        },
        {
            "user": "What's the environment variable to disable the github actions cache for a single job",
            "assistant": "I cannot reach the github actions",
            "user_label": "NO_MATCH",  # User marked as NO_MATCH
        },
        {
            "user": "I can't find the documentation for React hooks",
            "assistant": "Here's how React hooks work: useState, useEffect...",
            "user_label": "NO_MATCH",  # User having trouble, not assistant
        },
        {
            "user": "The docs are down, can you help me with Python decorators?",
            "assistant": "Sure! Python decorators are functions that modify other functions...",
            "user_label": "NO_MATCH",  # User having trouble, assistant helps
        },
        {
            "user": "I'm having trouble accessing the API documentation",
            "assistant": "I can help you with API concepts. What specifically do you need?",
            "user_label": "NO_MATCH",  # User having trouble, not assistant failing
        },
    ],
}

# Rules suggested by RainDrop DeepSearch (before Commander audit)
DEEPSEARCH_SUGGESTED_RULES = [
    {
        "id": "suggested-rule-1",
        "description": "The output must express the assistant failing to accessing documentation",
        "example": "I can't reach the Github Actions docs",
        "status": "pending_commander_audit",  # Waiting for Commander
    },
    {
        "id": "suggested-rule-2",
        "description": "The input must not be the user having trouble searching docs",
        "example": "I can't reach the Github Actions docs",
        "status": "pending_commander_audit",  # Waiting for Commander
    },
]

# Mock rules for quick demos
MOCK_RULES = [
    {
        "id": "rule-1",
        "description": "Fails to reach documentation",
        "examples": [
            {"text": "Kubernetes docs 404", "label": "MATCH"},
            {"text": "Can't reach K8s docs", "label": "MATCH"},
            {"text": "Documentation server is down", "label": "MATCH"},
            {"text": "Successfully loaded docs", "label": "NO_MATCH"},
            {"text": "User logged in", "label": "NO_MATCH"},
        ],
    },
    {
        "id": "rule-2",
        "description": "API authentication failure",
        "examples": [
            {"text": "401 Unauthorized", "label": "MATCH"},
            {"text": "Invalid API key", "label": "MATCH"},
            {"text": "Token expired", "label": "MATCH"},
            {"text": "200 OK response", "label": "NO_MATCH"},
            {"text": "Request successful", "label": "NO_MATCH"},
        ],
    },
    {
        "id": "rule-3",
        "description": "Database connection error",
        "examples": [
            {"text": "Failed to connect to database", "label": "MATCH"},
            {"text": "DB connection timeout", "label": "MATCH"},
            {"text": "Query executed successfully", "label": "NO_MATCH"},
        ],
    },
]


def get_deepsearch_issue():
    """Get the DeepSearch issue mock data."""
    return DEEPSEARCH_ISSUE


def get_suggested_rules():
    """Get rules suggested by DeepSearch."""
    return DEEPSEARCH_SUGGESTED_RULES


def get_common_issues():
    """Get list of common issues users can select from."""
    return COMMON_ISSUES


def get_mock_rule_by_id(rule_id: str):
    """Get a mock rule by ID."""
    return next((r for r in MOCK_RULES if r["id"] == rule_id), None)


def get_all_mock_rules():
    """Get all mock rules."""
    return MOCK_RULES


# Common issues that users can select from - diverse categories
COMMON_ISSUES = [
    "The assistant fails to search the internet to retrieve documentation",
    "The assistant provides incorrect code examples or syntax errors",
    "The assistant gives security vulnerabilities in code suggestions",
    "The assistant fails to handle rate limiting or API quota errors",
    "The assistant provides responses that violate user privacy or data protection",
    "The assistant fails to detect and handle timeout errors in API calls",
    "The assistant gives incorrect database query examples that could cause data loss",
    "The assistant fails to recognize when it doesn't have enough context to answer",
    "The assistant provides code that doesn't follow best practices or coding standards",
    "The assistant fails to identify and warn about potential performance bottlenecks",
]
