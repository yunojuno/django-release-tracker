from os import getenv

# Token used with the Platform API
HEROKU_API_TOKEN = getenv("HEROKU_API_TOKEN")

HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")

# Token used with the Github API
GITHUB_API_TOKEN = getenv("GITHUB_API_TOKEN")

# Username to whom the token belongs
GITHUB_USER_NAME = getenv("GITHUB_USER_NAME")

# Organisation to whom the source repo belongs
GITHUB_ORG_NAME = getenv("GITHUB_ORG_NAME")

# The source repo
GITHUB_REPO_NAME = getenv("GITHUB_REPO_NAME")

# Disable GH sync if you are deploying to multiple Heroku apps and you
# don't want a tag clash.
GITHUB_SYNC_ENABLED = getenv(
    "GITHUB_SYNC_ENABLED",
    all([GITHUB_API_TOKEN, GITHUB_USER_NAME, GITHUB_ORG_NAME, GITHUB_REPO_NAME]),
)
