---
title: "TrueNAS API Documentation"
hideTitle: true
description: "This website provides the full Application Programming Interface (API) documentation for TrueNAS versions starting with 25.04 and later."
linkTitle: "Home"
keywords:
 - TrueNAS API docs
 - TrueNAS Developers
 - TrueNAS WebSocket
---

The versioned JSON-RPC 2.0 Websocket Application Programming Interface (API) was introduced with TrueNAS 25.04.

Advanced users can interact with the TrueNAS API to perform management tasks using the [TrueNAS API Client](https://github.com/truenas/api_client) as an alternative to the TrueNAS web UI.
This websocket client provides the command line tool `midclt` and allows users to communicate with [TrueNAS middleware](https://github.com/truenas/middleware/) using Python by making API calls.
The client can connect to the local TrueNAS instance or to a specified remote socket.

Choose an API version to view the documentation:

{{< api_versions >}}

TrueNAS API documentation is also available from TrueNAS by appending `/api/docs/` to your TrueNAS host name or IP address in a browser.