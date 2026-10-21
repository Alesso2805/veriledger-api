# Back up and restore the database

The chain, the users and the peers all live in PostgreSQL. `deploy/backup.sh` and `deploy/restore.sh` wrap `pg_dump` and `pg_restore` for the stack of `deploy/docker-compose.prod.yml`. Run them from the repository root on the server (`/srv/veriledger` in [deploy.md](deploy.md)).

CI's `rehearsal` job checks the whole cycle on a throwaway stack on every pull request: it mines a block, backs up, drops every table, restores, and finds the block again.

## Back up

```bash
sh deploy/backup.sh
```

It writes `backups/veriledger-<UTC time>.dump`, a compressed `pg_dump --format=custom`, and prints its size. An empty dump is an error. Give a path as the first argument to write it somewhere else. `backups/` is ignored by git.

Every night, keeping two weeks, in the server's crontab:

```cron
0 3 * * * cd /srv/veriledger && sh deploy/backup.sh && find backups -name 'veriledger-*.dump' -mtime +14 -delete
```

A backup on the same disk does not survive the disk. Copy the dumps elsewhere as well, for example with `rclone` or `scp` to another machine.

Always back up before an update ([deploy.md](deploy.md), step 6). The migrations only go forward, and a rollback to an older version needs the database as it was.

## Restore

```bash
sh deploy/restore.sh backups/veriledger-20261021T030000Z.dump
```

It does three things:

1. It stops the API, so nothing writes while the data is replaced.
2. It runs `pg_restore --clean --if-exists --no-owner`, which drops what the dump holds and recreates it. A partly damaged database and an empty one both work.
3. It starts the API again.

Then check the stack:

```bash
sh deploy/verify.sh https://$DOMAIN
```

## After a restore

- Everything after the dump is gone: blocks mined, transactions sent, accounts created. Peers may hold a longer chain. The next `POST /nodes/resolve` adopts it if it is valid, so the network converges again.
- Sessions stay valid if `SECRET_KEY` did not change. A demo account created after the dump no longer exists, so its token answers 401.
- To roll back an update, restore the dump taken before it, then start the older images ([deploy.md](deploy.md), step 7).
