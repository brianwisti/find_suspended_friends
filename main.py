import json
import logging
from pathlib import Path

from dotenv import dotenv_values
from mastodon import Mastodon
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

# for dotenv
ENV_FILE = ".env"

logging.basicConfig(level="INFO", format="%(message)s", handlers=[RichHandler()])


def stored(func):
    """
    Utilize a file cache for the decorated function.

    If the cache does not exist, call the function and store the result. Otherwise, load from cache.
    """

    def inner(*args, **kwargs):
        func_name = func.__name__
        logging.debug("stored.inner for %s", func_name)
        cache_file = Path(f"{func_name}.json")

        if cache_file.is_file():
            logging.info("Loading data from %s", str(cache_file))
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


def accounts_table(accounts):
    """Return a Rich table summary of provided accounts."""
    logging.debug(accounts[0].keys())
    columns = [
        ["acct"],
        ["url"],
        ["last_status_at"],
        ["follower"],
        ["following"],
    ]
    table = Table(title="Suspended Accounts", show_footer=True)

    table.add_column("row", "row", style="green")

    for column in columns:
        column_name = column[0]
        table.add_column(column_name, column_name)

    row_index = 0

    for account in accounts:
        row_index += 1
        values = [str(account.get(column[0])) for column in columns]
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

    related_accounts = {}

    for account in followers_me:
        handle = account["acct"]

        if handle not in related_accounts:
            related_accounts[handle] = account
            related_accounts[handle]["following"] = False

        related_accounts[handle]["follower"] = True

    for account in following_me:
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

    logging.debug(suspended_accounts)
    logging.info("%s accounts appear to be suspended", len(suspended_accounts))
    console = Console()
    table = accounts_table(suspended_accounts)
    console.print(table)


if __name__ == "__main__":
    main()
