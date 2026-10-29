---
name: rocket-billing-account
description: "Read Rocket.net account information, usage, hosting plan, and billing. Use when the user wants to check account status, usage, plan, or invoices. Read-first; payment actions stay manual."
---

# Rocket.net billing and account

Covers account profile, hosting plan, usage, billing addresses, payment methods, and invoices.

## Account profile

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" account me
```

Or:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.account_controller.account_me_get
```

Update account settings:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.account_controller.account_me_patch --data '{"name":"New Name"}'
```

## Usage

Account-level resource usage:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" account usage
```

Or:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.account_controller.account_usage_get
```

Site-level usage:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.sites_controller.sites_id_usage_get --param id=<site_id>
```

## Hosting plan

Get current plan:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.account_controller.get_hosting_plan
```

## Account tasks

List background tasks at the account level:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.account_controller.account_tasks_get
```

## Billing addresses

List addresses:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.billing_controller.get_billing_addresses
```

Get a specific address:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.billing_controller.get_billing_addresses_address_id --param address_id=<address_id>
```

## Payment methods

List payment methods:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.billing_controller.get_billing_payment_methods
```

Get a specific payment method:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.billing_controller.get_billing_payment_methods_method_id --param payment_method_id=<payment_method_id>
```

## Invoices

List invoices:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.billing_controller.get_billing_invoices
```

Get a specific invoice:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.billing_controller.get_billing_invoices_invoice_id --param invoice_id=<invoice_id>
```

Download invoice PDF:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.billing_controller.get_billing_invoices_invoice_id_pdf --param invoice_id=<invoice_id>
```

## Billing SSO

Get a cookie for billing portal access:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.account_controller.account_billing_sso_post
```

## Payment actions - keep manual

Do not initiate payments, subscriptions, or billing mutations on the user's behalf. Present the relevant invoice ID or payment method ID and let the user act. The endpoints for credit card payment (`post_billing_invoices_invoice_id_credit_card_payment`) and PayPal subscription exist in the API but should not be called by Claude.

## Safety summary

All read endpoints: safe. Account settings patch: non-destructive. Payment and billing mutations: present data only, do not execute.
