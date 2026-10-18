"""Regenerate dark_mode.svg / light_mode.svg with live GitHub stats.

Runs daily via GitHub Actions. Standard library only, no dependencies.
Put your own details in profile.py; this file needs no edits.
"""
import html
import json
import os
import urllib.request
from datetime import datetime, timezone
from xml.etree import ElementTree

from profile import profileData

# --- layout ----------------------------------------------------------------
infoWidth = 56            # width of the info column, in characters
infoFontSize = 13         # info text size, in px
infoCharWidth = 7.8       # advance of one info character at infoFontSize
infoTop = 60              # baseline of the first info row
infoLineHeight = 21       # distance between info rows

# The Linux penguin (Tux) as a Unicode Braille pattern image. Each braille cell
# is 2 dots wide and 4 dots tall, so artLineHeight is twice artCellWidth to keep
# the dots square. Every line must have the same number of cells; keep it under
# ~62 columns so the info column still fits on the canvas.
artLeft = 30              # x of the art
artTop = 40               # baseline of the first art row
artCellWidth = 6.4        # width of one braille cell, in px
artLineHeight = 2 * artCellWidth
artFontSize = 10.7        # ~0.6em advance, roughly artCellWidth on common fonts
artInfoGap = 45           # space between the art and the info column
cardMargin = 30           # padding around the card contents
brailleBlank = "\u2800"   # an empty braille cell

tuxArt = """
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣴⣶⣾⣿⣿⣿⣿⣶⣶⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣤⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠿⣿⣷⣤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⣶⣾⣿⣿⣷⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣭⣭⡙⢿⣿⣿⣿⣿⣿⣿⣭⣍⡛⢿⣿⣿⣿⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⠟⣉⣉⣻⣎⣿⣿⣿⣿⣋⣁⣉⠹⢿⣆⣻⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡟⢉⣤⣄⠈⢿⣿⣿⡇⠀⣠⣶⣬⡉⠚⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⢸⣿⣿⡆⡼⠿⠿⢇⠀⣿⣿⣿⡇⠀⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣷⡈⠻⠋⠁⠀⠀⠈⠃⠀⠙⠻⢟⠁⣰⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⠗⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⡀⠙⣿⣿⣿⣿⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣏⣆⠀⠀⠀⠀⠀⠀⠀⠀⢀⡤⠊⠁⣰⣿⣿⡟⢿⣿⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡏⢶⠦⠤⠤⠤⠤⠒⠊⠁⣠⠴⠚⠙⣿⣿⣿⡄⢹⣿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⠇⠀⠙⢧⡖⣴⣠⡲⠬⠊⠁⠀⠀⠀⠘⣿⣿⣿⣿⣿⣿⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⣿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⣿⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⣿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⢀⡂⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⣷⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⣿⣿⣿⡀⠀⢀⡠⠄⠔⠐⠂⠒⡿⠋⠈⠉⠉⠈⠀⠁⠒⠢⠴⣿⣿⣷⡙⢿⣿⣿⣿⣿⣿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⣿⠏⣼⣿⠛⠉⠁⠁⠀⠀⠀⠀⠀⢰⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⢻⣿⣶⣍⢿⣿⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⡟⣸⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⡼⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣎⢻⣿⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⡟⣰⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣦⠹⣿⣿⣿⣿⣆⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⡟⣰⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣿⣿⡇⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⡿⢰⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⡇⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⣿⠇⣿⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡞⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⡇⣿⣿⣿⣿⣿⣯⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣿⣿⣆⢹⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⡰⠿⠿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⠿⠟⠿⣦⣙⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢳⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⠀⡿⢫⣴⣾⣿⣷⣦⢻⣿⡇⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⢀⠎⠀⠀⠀⠈⢻⣷⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⡂⠀⠉⣵⣿⣿⣿⣿⣿⡿⣸⡿⣁⠀⠀⠀⠀⠀⠀⠀
⠀⠀⢀⡤⢤⠤⣤⡴⡃⠀⠀⠀⠀⠀⠀⠹⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡃⠀⠀⣿⣿⣿⣿⣿⣿⣿⠟⠁⠈⣳⠀⠀⠀⠀⠀⠀
⠀⠀⡗⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣿⣷⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠅⠀⠀⠹⢿⣿⣿⣿⠿⠋⠀⠀⠀⢹⠀⠀⠀⠀⠀⠀
⠀⠀⡗⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⣶⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠁⠀⠀⠀⠀⠂⠐⠀⠀⠀⠀⠀⠀⠀⠱⢄⠀⠀⠀⠀
⠀⠀⢯⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⣿⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣎⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠱⣄⠀⠀
⠀⠀⢸⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢻⡛⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⡯⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢑⢵⠀
⠀⢠⠛⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⣾⣿⣿⣿⠧⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡀⡰⣌⠏⠀
⠀⢇⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠨⣹⢿⣶⣤⣤⣤⣀⣀⣤⣤⣤⣶⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⢠⡐⢦⣹⠦⠟⠉⠀⠀⠀
⠀⠋⠼⣰⡀⢆⠠⡀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡐⢼⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣎⠡⠀⠀⠀⠀⠀⡀⢄⠲⣬⢶⠛⠉⠁⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠉⠓⠙⠢⠝⣦⣣⣒⢤⡀⢄⠀⡀⢀⢀⠰⣌⣿⠟⠉⠀⠁⠀⠀⠀⠀⠀⠁⠈⠉⠉⠛⠛⠛⠿⢿⣿⣧⢳⡌⢦⡑⣎⡴⣫⡿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠛⠮⢷⣜⡶⣮⣿⠾⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠹⠿⣿⣿⣷⣿⡾⠟⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣀⡇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⠀⠇
"""

# Two tokens by design: the Actions GITHUB_TOKEN supplies the contribution-style
# commit counts (public + private activity), while an optional personal access
# token (ACCESS_TOKEN secret) can see private repositories for the repo list and
# the lines-of-code walk. Each one falls back to the other.
gitHubToken = os.environ.get("GITHUB_TOKEN") or os.environ.get("ACCESS_TOKEN") or ""
privateToken = os.environ.get("ACCESS_TOKEN") or gitHubToken


def resolvedUserName():
    name = profileData["userName"] or os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    if not name:
        raise SystemExit(
            'No username found. Set "userName" in profile.py or export GITHUB_REPOSITORY_OWNER.'
        )
    return name


def gitHubRequest(url, payload=None, token=None):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload else None,
        headers={
            "Authorization": f"Bearer {token or gitHubToken}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request) as response:
        return response.status, json.loads(response.read() or "{}")


def graphQlRequest(query, variables=None, token=None):
    _, responseBody = gitHubRequest(
        "https://api.github.com/graphql",
        {"query": query, "variables": variables or {}},
        token,
    )
    if responseBody.get("errors"):
        raise RuntimeError(responseBody["errors"])
    return responseBody["data"]


def fetchStats(userName):
    account = graphQlRequest(
        f"""
    query {{
      user(login: "{userName}") {{
        id
        createdAt
        followers {{ totalCount }}
        repositories(first: 100, ownerAffiliations: OWNER) {{
          totalCount
          nodes {{ name stargazerCount isFork }}
        }}
        repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) {{
          totalCount
        }}
      }}
    }}""",
        token=privateToken,
    )["user"]

    joinedYear = int(account["createdAt"][:4])
    yearAliases = "\n".join(
        f'y{year}: contributionsCollection(from: "{year}-01-01T00:00:00Z", to: "{year + 1}-01-01T00:00:00Z")'
        " { totalCommitContributions restrictedContributionsCount }"
        for year in range(joinedYear, datetime.now(timezone.utc).year + 1)
    )
    contributionYears = graphQlRequest(f'query {{ user(login: "{userName}") {{ {yearAliases} }} }}')["user"]
    commitCount = sum(
        yearStats["totalCommitContributions"] + yearStats["restrictedContributionsCount"]
        for yearStats in contributionYears.values()
    )

    profileStats = {
        "followers": account["followers"]["totalCount"],
        "repos": account["repositories"]["totalCount"],
        "contributed": account["repositoriesContributedTo"]["totalCount"],
        "stars": sum(node["stargazerCount"] for node in account["repositories"]["nodes"]),
        "commits": commitCount,
    }
    ownRepoNames = [node["name"] for node in account["repositories"]["nodes"] if not node["isFork"]]
    profileStats.update(countLinesOfCode(userName, ownRepoNames, account["id"]))
    return profileStats


locQuery = """
query($owner: String!, $name: String!, $id: ID!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef { target { ... on Commit {
      history(first: 100, author: {id: $id}, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { additions deletions }
      }
    } } }
  }
}"""


def countLinesOfCode(owner, repoNames, accountId):
    # GitHub's REST stats/contributors endpoint keeps answering 202 for the
    # Actions token, so walk this account's own commits on the default branch
    # through GraphQL instead.
    additions = deletions = 0
    for repoName in repoNames:
        cursor = None
        try:
            while True:
                defaultBranch = graphQlRequest(
                    locQuery,
                    {"owner": owner, "name": repoName, "id": accountId, "cursor": cursor},
                    token=privateToken,
                )["repository"]["defaultBranchRef"]
                if defaultBranch is None:
                    break  # empty repository
                history = defaultBranch["target"]["history"]
                additions += sum(node["additions"] for node in history["nodes"])
                deletions += sum(node["deletions"] for node in history["nodes"])
                if not history["pageInfo"]["hasNextPage"]:
                    break
                cursor = history["pageInfo"]["endCursor"]
        except Exception as error:
            print(f"loc {repoName}: {error}")
    return {"locAdded": additions, "locRemoved": deletions, "loc": additions - deletions}


palettes = {
    "dark": {"background": "#0d1117", "border": "#30363d", "art": "#8b949e", "heading": "#58a6ff",
             "key": "#ffa657", "value": "#c9d1d9", "dim": "#484f58", "added": "#3fb950", "removed": "#f85149"},
    "light": {"background": "#ffffff", "border": "#d0d7de", "art": "#57606a", "heading": "#0969da",
              "key": "#953800", "value": "#24292f", "dim": "#afb8c1", "added": "#1a7f37", "removed": "#cf222e"},
}


def keyValue(label, value, width=infoWidth):
    filler = "." * max(width - len(label) - len(str(value)) - 3, 1)
    return [(f"{label}: ", "key"), (filler + " ", "dim"), (str(value), "value")]


def optionalKeyValue(label, value, width=infoWidth):
    # An empty value in profile.py drops the whole row from the card.
    return keyValue(label, value, width) if value else []


def keyValuePair(labelOne, valueOne, labelTwo, valueTwo):
    left = keyValue(labelOne, valueOne, 30)
    return left + [(" | ", "dim")] + keyValue(labelTwo, valueTwo, 23)


def sectionRule(title=""):
    heading = f"─ {title} " if title else ""
    return [(heading, "heading"), ("─" * (infoWidth - len(heading)), "dim")]


def formatNumber(value):
    return f"{value:,}"


def infoLines(profileStats, userName):
    lines = [
        [(f"{userName.lower()}@github ", "heading"), ("─" * (infoWidth - len(userName) - 8), "dim")],
        [],
    ]
    lines += [
        optionalKeyValue("OS", profileData["operatingSystems"]),
        optionalKeyValue("Host", profileData["host"]),
        optionalKeyValue("Role", profileData["role"]),
        optionalKeyValue("IDE", profileData["ides"]),
        [],
        optionalKeyValue("Languages.Programming", profileData["programmingLanguages"]),
        optionalKeyValue("Languages.Spoken", profileData["spokenLanguages"]),
        optionalKeyValue("Hobbies", profileData["hobbies"]),
        [],
    ]
    contactRows = [row for row in (optionalKeyValue("Email", profileData["email"]),
                                   optionalKeyValue("LinkedIn", profileData["linkedIn"])) if row]
    if contactRows:
        lines.append(sectionRule("Contact"))
        lines += contactRows
        lines.append([])
    lines += [
        sectionRule("GitHub Stats"),
        keyValuePair(
            "Repos",
            f"{profileStats['repos']} {{Contributed: {profileStats['contributed']}}}",
            "Stars",
            formatNumber(profileStats["stars"]),
        ),
        keyValuePair("Commits", formatNumber(profileStats["commits"]), "Followers", formatNumber(profileStats["followers"])),
        [("Lines of Code: ", "key"), (formatNumber(profileStats["loc"]), "value"), (" ( ", "dim"),
         (formatNumber(profileStats["locAdded"]) + "++", "added"), (", ", "dim"),
         (formatNumber(profileStats["locRemoved"]) + "--", "removed"), (" )", "dim")],
    ]
    return lines


def renderCard(mode, profileStats, userName):
    colors = palettes[mode]
    artLines = tuxArt.strip("\n").split("\n")
    rows = infoLines(profileStats, userName)
    artColumns = max(len(artLine) for artLine in artLines)
    infoLeft = round(artLeft + artColumns * artCellWidth + artInfoGap)
    cardWidth = round(infoLeft + infoWidth * infoCharWidth + cardMargin)
    cardHeight = round(max(artTop + len(artLines) * artLineHeight,
                           infoTop + len(rows) * infoLineHeight) + cardMargin)
    outputLines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{cardWidth}" height="{cardHeight}" '
        f'viewBox="0 0 {cardWidth} {cardHeight}" font-family="Consolas, Menlo, monospace" '
        f'font-size="{infoFontSize}px">',
        f'<rect x="0.5" y="0.5" width="{cardWidth - 1}" height="{cardHeight - 1}" rx="10" '
        f'fill="{colors["background"]}" stroke="{colors["border"]}"/>',
    ]
    for index, artLine in enumerate(artLines):
        if not artLine.strip(brailleBlank):
            continue  # nothing drawn on this row
        # textLength pins every cell to artCellWidth px, so the dot grid stays
        # aligned no matter which font the renderer falls back to for braille.
        outputLines.append(
            f'<text x="{artLeft}" y="{round(artTop + index * artLineHeight)}" fill="{colors["art"]}" '
            f'font-family="DejaVu Sans Mono, Noto Sans Symbols2, Segoe UI Symbol, Apple Braille, monospace" '
            f'font-size="{artFontSize}px" textLength="{round(len(artLine) * artCellWidth, 2)}" '
            f'lengthAdjust="spacingAndGlyphs" xml:space="preserve">{html.escape(artLine)}</text>'
        )
    for index, segments in enumerate(rows):
        if not segments:
            continue
        spanMarkup = "".join(
            f'<tspan fill="{colors[color]}">{html.escape(text)}</tspan>' for text, color in segments
        )
        outputLines.append(
            f'<text x="{infoLeft}" y="{round(infoTop + index * infoLineHeight)}" xml:space="preserve">{spanMarkup}</text>'
        )
    outputLines.append("</svg>")
    return "\n".join(outputLines)


def selfCheck():
    assert len("".join(text for text, _ in keyValue("OS", "YOUR_OS"))) == infoWidth

    artLines = tuxArt.strip("\n").split("\n")
    assert len({len(artLine) for artLine in artLines}) == 1, "every art row needs the same cell count"
    assert all("\u2800" <= char <= "\u28ff" for artLine in artLines for char in artLine), "art must be braille"
    assert artLineHeight == 2 * artCellWidth, "braille dots stay square only at a 2:1 cell ratio"

    # nothing may be drawn outside the canvas
    emptyStats = {"repos": 0, "contributed": 0, "stars": 0, "commits": 0,
                  "followers": 0, "locAdded": 0, "locRemoved": 0, "loc": 0}
    svg = ElementTree.fromstring(renderCard("dark", emptyStats, "someone"))
    cardWidth, cardHeight = int(svg.get("width")), int(svg.get("height"))
    for element in svg.iter():
        if element.tag.endswith("text"):
            assert 0 <= float(element.get("x")) < cardWidth, "text starts past the card width"
            assert 0 <= float(element.get("y")) < cardHeight, "text sits below the card height"


if __name__ == "__main__":
    selfCheck()
    activeUserName = resolvedUserName()
    stats = fetchStats(activeUserName)
    print("stats:", stats)
    for mode in palettes:
        with open(f"{mode}_mode.svg", "w", encoding="utf-8") as svgFile:
            svgFile.write(renderCard(mode, stats, activeUserName))
    print("wrote dark_mode.svg, light_mode.svg")
