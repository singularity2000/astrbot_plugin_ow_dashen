# searchBnetAccount

This file documents only the upstream Dashen search interface captured in `180_Full.txt`.

Sensitive values in examples are masked:

- `token` -> `<TOKEN>`
- `roleId` -> `<ROLE_ID>`
- `bnetId` -> `<BNET_ID>`
- `customerToken` -> `<CUSTOMER_TOKEN>`
- `Cookie` / `GL-Uid` / `GL-DeviceId` / `traceId` -> `<MASKED>`

## Endpoint

`POST https://datamsapi.ds.163.com/v1/a19ld5tool/searchBnetAccount`

Current `overstats` client constant:

- `SEARCH_BNET_ACCOUNT_URL = "https://datamsapi.ds.163.com/v1/a19ld5tool/searchBnetAccount"`

## Purpose

Resolve a BattleTag such as `GrowlR#5632` into:

- `bnetId`
- `customerToken`
- player display info

This is the upstream search step used before profile / match / summary / rank-history flows.

## Request

### Required JSON body

```json
{
  "token": "<TOKEN>",
  "roleId": "<ROLE_ID>",
  "dts": "2026",
  "server": "1",
  "name": "GrowlR#5632"
}
```

Field notes:

- `token`: Dashen account token
- `roleId`: role id for the Dashen account
- `dts`: current season / bigdata dts value
- `server`: region/server id, normally `"1"`
- `name`: target BattleTag

### Important headers

From the captured request in `180_Full.txt`, the meaningful headers are:

- `Accept: application/json, text/plain, */*`
- `Content-Type: application/json;charset=UTF-8`
- `GL-ClientType: 60`
- `Origin: https://act.ds.163.com`
- `Referer: https://act.ds.163.com/`
- `User-Agent: Mozilla/5.0 ... app/df_client ...`

Captured but sensitive / session-bound headers should not be copied into docs as real values:

- `Cookie`
- `GL-CheckSum`
- `GL-DeviceId`
- `GL-Uid`
- `GL-X-XSRF-TOKEN`

## Response

### Success example

```json
{
  "code": 0,
  "data": {
    "bnetId": "<BNET_ID>",
    "name": "GrowlR#5632",
    "icon": "https://ld5picproxy.ds.163.com/overwatch/<MASKED>.png",
    "title": "string",
    "titleIcon": "https://ld5picproxy.ds.163.com/overwatch/<MASKED>.png",
    "level": 4,
    "gameTime": "1063.29",
    "totalMatchNum": 123,
    "customerToken": "<CUSTOMER_TOKEN>"
  },
  "success": true,
  "traceId": "<MASKED>"
}
```

### Response field notes

- `code == 0`: request succeeded
- `success == true`: request succeeded
- `data.bnetId`: numeric Battle.net id
- `data.name`: normalized BattleTag
- `data.icon`: avatar URL
- `data.title`: player title text
- `data.titleIcon`: title icon URL
- `data.level`: title level / display level
- `data.gameTime`: total game time string
- `data.totalMatchNum`: total match count
- `data.customerToken`: token used by later gameplay/stat endpoints
- `traceId`: upstream trace id

## Raw Capture Mapping

The body in `180_Full.txt`:

```json
{
  "token": "<TOKEN>",
  "roleId": "<ROLE_ID>",
  "dts": "2026",
  "server": "1",
  "name": "GrowlR#5632"
}
```

maps to a response body like:

```json
{
  "code": 0,
  "data": {
    "bnetId": "<BNET_ID>",
    "name": "GrowlR#5632",
    "icon": "https://ld5picproxy.ds.163.com/overwatch/<MASKED>.png",
    "title": "string",
    "titleIcon": "https://ld5picproxy.ds.163.com/overwatch/<MASKED>.png",
    "level": 4,
    "gameTime": "1063.29",
    "totalMatchNum": 123,
    "customerToken": "<CUSTOMER_TOKEN>"
  },
  "success": true,
  "traceId": "<MASKED>"
}
```

## Notes

- The raw `title` text in `180_Full.txt` looks garbled because the captured file encoding is not fully normalized.
- `customerToken` is the key output used by the rest of the Dashen data requests.
- In current code, this request is built in `DashenAPIClient.search_bnet_account()`.
