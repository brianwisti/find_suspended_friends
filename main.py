import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import dotenv_values
from mastodon import Mastodon
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

# for dotenv
ENV_FILE = ".env"

SUSPENDED_TABLE_COLUMNS = [
    ("url", "green"),
    ("acct", "white"),
    ("last_status_at", "white"),
    ("follower", "blue"),
    ("following", "blue"),
]
# how long to hold onto cache files
CACHE_LIFESPAN = timedelta(hours=1)

# When did this script start running?
NOW = datetime.now()

logging.basicConfig(level="INFO", format="%(message)s", handlers=[RichHandler()])


def stored(func):
    """
    Utilize a file cache for the decorated function.

    - if the cache exists and is younger than ``CACHE_LIFESPAN``, use it
    - otherwise, call the function and store the result
    """

    def inner(*args, **kwargs):
        func_name = func.__name__
        logging.debug("stored.inner for %s", func_name)
        cache_file = Path(f"{func_name}.json")

        if cache_file.is_file():
            logging.debug("Cache file %s exists", cache_file)
            cache_written_at = datetime.fromtimestamp(cache_file.stat().st_mtime)
            logging.debug("Cache file written at %s", cache_written_at)

            if NOW - cache_written_at < CACHE_LIFESPAN:
                logging.info("Loading data from %s", cache_file)
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                return data

        logging.info("Calling %s", func_name)
        data = func(*args, **kwargs)

        logging.info("Writing data to %s", cache_file)
        cache_file.write_text(json.dumps(data, indent=4, default=str), encoding="utf-8")

        return data

    return inner


@stored
def instance_summary(mastodon: Mastodon):
    """Return a dictionary of information about the connected instance."""
    instance = mastodon.instance()
    fields = ["uri", "title", "short_description"]
    data = {field: instance[field] for field in fields}
    data["contact_account"] = instance["contact_account"]["display_name"]

    return data


@stored
def my_info(mastodon: Mastodon):
    """Return a dictionary of information about the logged in user."""
    return mastodon.me()


@stored
def following(mastodon: Mastodon, user_id: int):
    """Fetches and returns a list of users a given user is following."""
    accounts = mastodon.account_following(user_id)
    accounts = mastodon.fetch_remaining(accounts)

    return accounts


@stored
def followers(mastodon: Mastodon, user_id: int):
    """Fetches and returns a list of followers for the given user."""
    accounts = mastodon.account_followers(user_id)
    accounts = mastodon.fetch_remaining(accounts)

    return accounts


@stored
def my_suspended_acquaintances(followers, following):
    """
    Identify known accounts that have some relation to me.

    Relation is either: they follow me or I follow them.
    """
    related_accounts = {}

    for account in followers:
        handle = account["acct"]

        if handle not in related_accounts:
            related_accounts[handle] = account
            related_accounts[handle]["following"] = False

        related_accounts[handle]["follower"] = True

    for account in following:
        handle = account["acct"]

        if handle not in related_accounts:
            related_accounts[handle] = account
            related_accounts[handle]["follower"] = False

        related_accounts[handle]["following"] = True

    suspended_accounts = [
        account
        for handle, account in related_accounts.items()
        if account.get("suspended")
    ]
    suspended_accounts.sort(key=lambda account: account["acct"])

    return suspended_accounts


@stored
def suspended_table_rows(accounts):
    """Filter accounts to columns used for table summary."""
    return [
        {column: row[column] for column, _ in SUSPENDED_TABLE_COLUMNS}
        for row in accounts
    ]


def accounts_table(accounts):
    """Return a Rich table summary of provided accounts."""
    logging.debug(accounts[0].keys())
    table = Table(show_footer=True)
    table.add_column("row", "row", style="bold green")

    for column_name, style in SUSPENDED_TABLE_COLUMNS:
        table.add_column(column_name, column_name, style=style)

    # cache more for information sharing than for optimization
    account_rows = suspended_table_rows(accounts)
    row_index = 0

    for account in account_rows:
        row_index += 1
        values = [str(account.get(column)) for column, _ in SUSPENDED_TABLE_COLUMNS]
        table.add_row(str(row_index), *values)

    return table


def main():
    """Print accounts connected to me that are labeled as suspended."""
    config = dotenv_values(ENV_FILE)
    logging.info(config)
    mastodon = Mastodon(**config)
    logging.debug(instance_summary(mastodon))
    this_user = my_info(mastodon)
    logging.debug(this_user)
    followers_me = followers(mastodon, this_user["id"])
    logging.info("%s followers", len(followers_me))
    following_me = following(mastodon, this_user["id"])
    logging.info("%s following", len(following_me))
    logging.debug(followers_me)
    logging.debug(following_me)

    suspended_accounts = my_suspended_acquaintances(
        followers=followers_me, following=following_me
    )

    logging.debug(suspended_accounts)
    console = Console()
    table = accounts_table(suspended_accounts)
    console.print(table)
    logging.info("%s accounts appear to be suspended", len(suspended_accounts))


if __name__ == "__main__":
    main()
