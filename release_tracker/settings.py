from os import getenv

# Token used with the Platform API
HEROKU_API_TOKEN = getenv("HEROKU_API_TOKEN")

# Values set by dyno runtime metadata
HEROKU_APP_ID = getenv("HEROKU_APP_ID")
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
HEROKU_RELEASE_CREATED_AT = getenv("HEROKU_RELEASE_CREATED_AT")
HEROKU_RELEASE_VERSION = getenv("HEROKU_RELEASE_VERSION")
HEROKU_SLUG_COMMIT = getenv("HEROKU_SLUG_COMMIT")
HEROKU_SLUG_DESCRIPTION = getenv("HEROKU_SLUG_DESCRIPTION")

# If this is False then we can't automatically created releases
HEROKU_LABS_ENABLED = all(
    [
        HEROKU_APP_ID,
        HEROKU_APP_NAME,
        HEROKU_RELEASE_CREATED_AT,
        HEROKU_RELEASE_VERSION,
        HEROKU_SLUG_COMMIT,
        HEROKU_SLUG_DESCRIPTION,
    ]
)

# Token used with the Github API
GITHUB_API_TOKEN = getenv("GITHUB_API_TOKEN")

# Username to whom the token belongs
GITHUB_USER_NAME = getenv("GITHUB_USER_NAME")

# Organisation to whom the source repo belongs
GITHUB_ORG_NAME = getenv("GITHUB_ORG_NAME")

# The source repo
GITHUB_REPO_NAME = getenv("GITHUB_REPO_NAME")

GITHUB_ENABLED = all(
    [
        GITHUB_API_TOKEN,
        GITHUB_USER_NAME,
        GITHUB_ORG_NAME,
        GITHUB_REPO_NAME,
    ]
)
