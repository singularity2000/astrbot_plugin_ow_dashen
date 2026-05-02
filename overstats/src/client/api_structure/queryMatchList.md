# queryMatchList

This file documents the upstream Dashen match list endpoint captured in `659_Full.txt`.

Sensitive values in examples are masked:

- `GL-Bigdata-Auth-Token` -> `<TOKEN>`
- `GL-Bigdata-Role-Id` -> `<ROLE_ID>`
- `token` query param -> `<CUSTOMER_TOKEN>`
- `Cookie` / `GL-Uid` / `GL-DeviceId` / `traceId` -> `<MASKED>`

## Endpoint

`GET https://datamsapi.ds.163.com/v1/a19ld5tool/customer/queryMatchList`

Current `overstats` client method:

- `DashenAPIClient.query_match_list(customer_token, game_mode, page=1, season=None)`

## Purpose

Query a player's recent match list.

The capture in `659_Full.txt` is the competitive list variant:

- `gameMode=sport`

This endpoint is used to fetch recent match summaries before:

- rendering match list cards
- selecting a match by index
- loading match details for a chosen record

## Request

### Query parameters

Masked example:

```text
gameMode=sport
page=1
season=
token=<CUSTOMER_TOKEN>
```

Field notes:

- `gameMode`: mode selector, captured value is `sport`
- `page`: result page number
- `season`: optional season number; empty in the capture
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
  "data": [
    {
      "mapGuid": "string",
      "matchId": "string",
      "matchRet": 1,
      "instanceType": "IT_RANKED",
      "heroGuid": "string",
      "roleType": "healer",
      "heroIcon": "https://...png",
      "teamScore": 3,
      "opponentScore": 1,
      "kill": 15,
      "assist": 16,
      "death": 4,
      "heroDamage": 4631,
      "cure": 6801,
      "resistDamage": 0,
      "rankInfo": {},
      "beginTs": 1777212060658,
      "gameMode": "SportPreset"
    }
  ],
  "success": true,
  "traceId": "<MASKED>"
}
```

### Important response fields

- `code == 0`: request succeeded
- `success == true`: request succeeded
- `data`: recent match summary list
- `traceId`: upstream trace id

## Match Item Fields

Example abbreviated item:

```json
{
  "mapGuid": "576460752303424195",
  "matchId": "c788c713-75a8-a744-bad7-cfd08705cdf4",
  "matchRet": 1,
  "instanceType": "IT_RANKED",
  "heroGuid": "207165582859043685",
  "roleType": "healer",
  "heroIcon": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/<MASKED>.png",
  "teamScore": 3,
  "opponentScore": 1,
  "kill": 15,
  "killMax": false,
  "assist": 16,
  "death": 4,
  "heroDamage": 4631,
  "heroDamageMax": false,
  "cure": 6801,
  "cureMax": false,
  "resistDamage": 0,
  "resistDamageMax": false,
  "rankInfo": {
    "rank_name": "Platinum",
    "rankName": "Platinum",
    "rank_sub_tier": 5,
    "rankSubTier": 5,
    "rankScore": 395,
    "ts": 1777212060658
  },
  "beginTs": 1777212060658,
  "gameMode": "SportPreset"
}
```

Field notes:

- `mapGuid`: map id
- `matchId`: match id
- `matchRet`: result, usually `1` win / `-1` loss
- `instanceType`: match type, captured value is `IT_RANKED`
- `heroGuid`: hero id
- `roleType`: role type such as `tank` / `dps` / `healer`
- `heroIcon`: hero icon URL
- `teamScore` / `opponentScore`: final score
- `kill`, `assist`, `death`: summary stats
- `heroDamage`, `cure`, `resistDamage`: summary combat stats
- `rankInfo`: rank snapshot at the time of the match
- `beginTs`: match start timestamp
- `gameMode`: upstream mode label, here `SportPreset`

## `rankInfo`

Example shape:

```json
{
  "rank_name": "Platinum",
  "rankName": "Platinum",
  "rank_sub_tier": 5,
  "rankSubTier": 5,
  "rankScore": 395,
  "ts": 1777212060658
}
```

Meaning:

- current rank snapshot associated with that match record
- contains both snake_case and camelCase naming from upstream

## Raw Capture Mapping

The request in `659_Full.txt` is:

```text
GET /v1/a19ld5tool/customer/queryMatchList?gameMode=sport&page=1&season=&token=<CUSTOMER_TOKEN>
```

with Bigdata auth headers:

```text
GL-Bigdata-Auth-Token: <TOKEN>
GL-Bigdata-Dts: 2026
GL-Bigdata-Role-Id: <ROLE_ID>
GL-Bigdata-Server: 1
```

and returns a list of recent competitive matches.

## Notes

- This capture is the competitive (`sport`) variant of `queryMatchList`.
- There are other variants in code, including leisure and fight-mode list endpoints.
- The full payload is much smaller than match detail endpoints because each item is only a summary row.
