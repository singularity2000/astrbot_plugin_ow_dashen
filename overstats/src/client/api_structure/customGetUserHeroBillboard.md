# customGetUserHeroBillboard

This file documents the upstream Dashen user hero billboard endpoint captured in `418_Full.txt`.

Sensitive values in examples are masked:

- `GL-Bigdata-Auth-Token` -> `<TOKEN>`
- `GL-Bigdata-Role-Id` -> `<ROLE_ID>`
- `token` query param -> `<CUSTOMER_TOKEN>`
- `bnetId` -> `<BNET_ID>`
- `Cookie` / `GL-Uid` / `GL-DeviceId` / `traceId` -> `<MASKED>`

## Endpoint

`GET https://datamsapi.ds.163.com/v1/a19ld5tool/billboard/customGetUserHeroBillboard`

Current `overstats` client method:

- `DashenAPIClient.get_billboard_user(customer_token)`

## Purpose

Query a player's hero billboard / province ranking summary.

This endpoint returns hero ranking records for the target player, grouped by competitive mode buckets such as:

- `sportPresetHeroBillboardList`
- `sportOpenHeroBillboardList`

## Request

### Query parameters

Masked example:

```text
token=<CUSTOMER_TOKEN>
```

Field notes:

- `token`: customer token resolved from `searchBnetAccount`

### Important headers

The captured request includes:

- `Accept: application/json, text/plain, */*`
- `GL-Bigdata-Auth-Token: <TOKEN>`
- `GL-Bigdata-Dts: 2026`
- `GL-Bigdata-Role-Id: <ROLE_ID>`
- `GL-Bigdata-Server: 1`
- `GL-ClientType: 60`
- `Origin: https://act.ds.163.com`
- `Referer: https://act.ds.163.com/`
- `User-Agent: Mozilla/5.0 ... app/df_client ...`

Sensitive or session-bound headers should be masked in docs:

- `Cookie`
- `GL-DeviceId`
- `GL-Uid`
- `GL-X-XSRF-TOKEN`

## Response

### Success shape

```json
{
  "code": 0,
  "data": {
    "bnetId": "<BNET_ID>",
    "sportOpenHeroBillboardList": [],
    "sportPresetHeroBillboardList": []
  },
  "success": true,
  "traceId": "<MASKED>"
}
```

### Important response fields

- `code == 0`: request succeeded
- `success == true`: request succeeded
- `data.bnetId`: numeric Battle.net id
- `data.sportOpenHeroBillboardList`: open-queue hero billboard rows
- `data.sportPresetHeroBillboardList`: role-queue / preset competitive hero billboard rows
- `traceId`: upstream trace id

## `sportPresetHeroBillboardList`

Example abbreviated item:

```json
{
  "userName": "",
  "rankNum": 1860,
  "rankedLevel": 2082,
  "matchSum": 11,
  "winRate": 72.73,
  "province": "string",
  "heroGuid": "207165582859043612"
}
```

Field notes:

- `userName`: player display name
- `rankNum`: province ranking position for this hero
- `rankedLevel`: billboard score / rank level
- `matchSum`: hero match count
- `winRate`: hero win rate
- `province`: province / region name
- `heroGuid`: hero id

## `sportOpenHeroBillboardList`

In the capture, this field is empty:

```json
[]
```

When data exists, the item structure is expected to be similar to `sportPresetHeroBillboardList`.

## Raw Capture Mapping

The request in `418_Full.txt` is:

```text
GET /v1/a19ld5tool/billboard/customGetUserHeroBillboard?token=<CUSTOMER_TOKEN>
```

with Bigdata auth headers:

```text
GL-Bigdata-Auth-Token: <TOKEN>
GL-Bigdata-Dts: 2026
GL-Bigdata-Role-Id: <ROLE_ID>
GL-Bigdata-Server: 1
```

and returns a hero billboard payload like:

```json
{
  "code": 0,
  "data": {
    "bnetId": "<BNET_ID>",
    "sportOpenHeroBillboardList": [],
    "sportPresetHeroBillboardList": [
      {
        "userName": "",
        "rankNum": 1860,
        "rankedLevel": 2082,
        "matchSum": 11,
        "winRate": 72.73,
        "province": "string",
        "heroGuid": "207165582859043612"
      }
    ]
  },
  "success": true,
  "traceId": "<MASKED>"
}
```

## Notes

- The raw `province` text in the capture looks garbled because the capture text encoding is not fully normalized.
- This endpoint is used for player hero billboard / province-rank style overlays.
- It is different from `queryCard` and `queryCountInfo`: this one focuses on hero-level ranking entries, not profile card data or aggregate statistics.
