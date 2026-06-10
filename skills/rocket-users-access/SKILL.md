---
name: rocket-users-access
description: "Manage site users, roles, SSH keys, FTP accounts, and password protection on Rocket.net. Use when the user wants to grant or revoke site access, manage SSH or FTP credentials, or set password protection."
---

# Rocket.net users and access

Covers site collaborators, SSH keys, FTP accounts, and HTTP password protection.

## Site users (collaborators)

List users on a site:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.site_users_controller.sites_id_users_get --param id=<site_id>
```

Invite a user to a site:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.site_users_controller.sites_id_users_post --param id=<site_id> --data '{"email":"colleague@example.com","role":"editor"}'
```

Reinvite a user:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.site_users_controller.sites_id_users_user_id_reinvite_post --param id=<site_id> --param user_id=<user_id>
```

Remove a user from a site - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.site_users_controller.sites_id_users_user_id_delete --param id=<site_id> --param user_id=<user_id> --yes
```

## Account-level users

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
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.ssh_keys_controller.sites_id_ssh_keys_get --param id=<site_id>
```

Add an SSH key:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.ssh_keys_controller.sites_id_ssh_keys_post --param id=<site_id> --data '{"name":"my-key","public_key":"ssh-rsa AAAA..."}'
```

Authorize an SSH key:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.ssh_keys_controller.sites_id_ssh_keys_authorize_post --param id=<site_id> --data '{"name":"my-key"}'
```

Deauthorize an SSH key - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.ssh_keys_controller.sites_id_ssh_keys_deauthorize_post --param id=<site_id> --data '{"name":"my-key"}' --yes
```

Delete all SSH keys - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.ssh_keys_controller.sites_id_ssh_keys_delete --param id=<site_id> --yes
```

## FTP accounts

List FTP accounts:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.ftp_accounts_controller.sites_id_ftp_accounts_get --param id=<site_id>
```

Create an FTP account:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.ftp_accounts_controller.sites_id_ftp_accounts_post --param id=<site_id> --data '{"username":"ftpuser","password":"...","path":"/"}'
```

Update FTP account:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.ftp_accounts_controller.sites_id_ftp_accounts_patch --param id=<site_id> --data '{"username":"ftpuser","password":"newpass"}'
```

Delete FTP account - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.ftp_accounts_controller.sites_id_ftp_accounts_delete --param id=<site_id> --data '{"username":"ftpuser"}' --yes
```

## Password protection

Get current password protection state:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.password_protection_controller.sites_id_password_protection_get --param id=<site_id>
```

Enable password protection:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.password_protection_controller.sites_id_password_protection_post --param id=<site_id> --data '{"enabled":true}'
```

List protected users:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.password_protection_controller.sites_id_password_protection_users_get --param id=<site_id>
```

Add a protected user:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.password_protection_controller.sites_id_password_protection_users_post --param id=<site_id> --data '{"username":"visitor","password":"..."}'
```

Remove a protected user - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.password_protection_controller.sites_id_password_protection_users_user_id_delete --param id=<site_id> --param user_id=<user_id> --yes
```

Disable password protection - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.password_protection_controller.sites_id_password_protection_delete --param id=<site_id> --yes
```

## Safety summary

List and invite: safe. Delete user, deauthorize SSH, delete FTP, disable password protection: all require --yes. Read before revoking access.
