---
name: rocket-users-access
description: "Manage site users, roles, SSH keys, FTP accounts, and password protection on Rocket.net. Use when the user wants to grant or revoke site access, manage SSH or FTP credentials, or set password protection."
---

# Rocket.net users and access

Covers site collaborators, SSH keys, FTP accounts, and HTTP password protection. Every operation below has an ergonomic subcommand; the generic `call` form is listed only for the few endpoints without one. Global flags (`--json`, `--yes`) go AFTER the subcommand.

## Site users (collaborators)

List users on a site:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py users list <site_id>
```

Invite a user to a site (the API takes a display name and an email):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py users add <site_id> --name "Colleague Name" --email colleague@example.com
```

Remove a user from a site - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py users remove <site_id> <user_id> --yes
```

Reinvite a site user (no subcommand, generic call):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.site_users_controller.sites_id_users_user_id_reinvite_post --param id=<site_id> --param user_id=<user_id>
```

## Account-level users

No subcommands for these; use generic call.

List all users in the account:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.users_controller.users_get
```

Invite a new account user:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.users_controller.users_post --data '{"email":"new@example.com","role":"viewer"}'
```

Delete an account user - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.users_controller.users_user_id_delete --param user_id=<user_id> --yes
```

## SSH keys

List SSH keys on a site:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssh list <site_id>
```

Add an SSH key, from a file or inline:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssh add <site_id> --name my-key --key-file ~/.ssh/id_ed25519.pub
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssh add <site_id> --name my-key --key "ssh-ed25519 AAAA..." [--passphrase ...]
```

Authorize an SSH key:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssh authorize <site_id> --name my-key
```

Deauthorize an SSH key - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssh deauthorize <site_id> --name my-key --yes
```

Remove an SSH key - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssh remove <site_id> --name my-key --yes
```

## FTP accounts

List FTP accounts:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ftp list <site_id>
```

Create an FTP account. The API requires ALL five fields:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ftp add <site_id> --username ftpuser --password '...' --homedir / --quota 1024 --domain example.com
```

Update an FTP account (any of password, quota, homedir):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ftp update <site_id> --password 'newpass' --quota 2048
```

Delete an FTP account - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ftp remove <site_id> --username ftpuser --yes
```

## SFTP and SSH credentials

The site's own SFTP username and password (returned in plaintext, treat accordingly):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py credentials <site_id>
```

## Password protection

Get current state:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py pwprotect status <site_id>
```

Enable protection:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py pwprotect enable <site_id>
```

List protection users:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py pwprotect users <site_id>
```

Add a protection user:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py pwprotect add-user <site_id> --username visitor --password '...'
```

Remove a protection user - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py pwprotect remove-user <site_id> <user_id> --yes
```

Disable protection - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py pwprotect disable <site_id> --yes
```

## Safety summary

List, add, invite, authorize, enable: no confirmation. Remove user, remove or deauthorize SSH key, remove FTP account, remove protection user, disable protection: all require --yes. Read before revoking access.
