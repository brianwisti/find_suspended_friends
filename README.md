# find_suspended_friends

Extremely rough. Just sharing because the basic logic may be useful to someone else.

It's supposed to help me find Mastodon accounts of both people I follow and people that follow me which are listed as suspended by my current instance.

This is identifying fallout from a bug late last year where mastodon.social was marking accounts as suspended even when they weren't. This flagged those accoounts for all federated instances. Although the bug was fixed, the federated suspensions remain.

- [Accounts are being suspended without any admin action #22425](https://github.com/mastodon/mastodon/issues/22425)

I'll do more homework on the actual cause when I'm not so tired. All I know for sure is roughly 10% of the accounts I followed or was followed by — and all from mastodon.social — are listed as suspended by my instance. I don't see their posts or their replies to my posts. I got tired of identifying the accounts one at a time.

## Usage

Assumes a developer application token registered with your instance.

Needs a `.env` file that looks something like this:

```
client_id="..."
client_secret="..."
access_token="..."
api_base_url="https://..."
```

Replace placeholders with your developer application information, and use the URL of the instance your application is registered with.

```sh
python -m pip install -r requirements.txt
```

Run it. There are currently no options.

```sh
python main.py
```

Bask in the beauty of a table listing accounts that your instance thinks are suspended. An empty table if you're lucky.
