# queryMatchInfo

This file documents the upstream Dashen match detail endpoint captured in `672_Full.txt`.

Sensitive values in examples are masked:

- `GL-Bigdata-Auth-Token` -> `<TOKEN>`
- `GL-Bigdata-Role-Id` -> `<ROLE_ID>`
- `token` query param -> `<CUSTOMER_TOKEN>`
- `bnetId` -> `<BNET_ID>`
- `customerToken` -> `<CUSTOMER_TOKEN>`
- `Cookie` / `GL-Uid` / `GL-DeviceId` / `traceId` -> `<MASKED>`

## Endpoint

`GET https://datamsapi.ds.163.com/v1/a19ld5tool/customer/queryMatchInfo`

Current `overstats` client method:

- `DashenAPIClient.query_match_info(customer_token, match_id)`

## Purpose

Query a single normal competitive match detail.

Compared with `queryMatchList`, this endpoint returns a full match payload including:

- match-level summary
- hero usage summary
- teammate list
- enemy list
- perk selections
- ban hero data

## Request

### Query parameters

Masked example:

```text
matchId=c788c713-75a8-a744-bad7-cfd08705cdf4
season=
token=<CUSTOMER_TOKEN>
```

Field notes:

- `matchId`: target match id
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
  "data": {
    "matchRet": 1,
    "mapGuid": "string",
    "gameTimeSec": 955,
    "startTime": 1777212060,
    "teamScore": 3,
    "opponentScore": 1,
    "heroList": [],
    "teammateList": [],
    "enemyList": [],
    "teamBanHeroGuids": [],
    "enemyBanHeroGuids": []
  },
  "success": true,
  "traceId": "<MASKED>"
}
```

### Important response fields

- `code == 0`: request succeeded
- `success == true`: request succeeded
- `data.matchRet`: match result
- `data.mapGuid`: map id
- `data.gameTimeSec`: match duration in seconds
- `data.startTime`: start timestamp
- `data.teamScore` / `data.opponentScore`: final score
- `data.heroList`: target player's hero usage summary for this match
- `data.teammateList`: ally player list
- `data.enemyList`: enemy player list
- `data.teamBanHeroGuids`: team-side banned heroes
- `data.enemyBanHeroGuids`: enemy-side banned heroes
- `traceId`: upstream trace id

## `heroList`

Example abbreviated item:

```json
{
  "heroId": "207165582859043685",
  "userTimeSec": 690,
  "useTimeRate": "100.00",
  "statMap": {
    "603482350067647492": 6.0,
    "603482350067647671": 4630.619554758072
  }
}
```

Field notes:

- `heroId`: hero id
- `userTimeSec`: time used on this hero
- `useTimeRate`: usage share in percent
- `statMap`: upstream stat-id to numeric-value map

## `teammateList` / `enemyList`

Example abbreviated item:

```json
{
  "name": "GrowlR#5632",
  "bnetId": "<BNET_ID>",
  "customerToken": "<CUSTOMER_TOKEN>",
  "heroGuid": "207165582859043685",
  "heroIcon": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/<MASKED>.png",
  "kill": 15,
  "assist": 16,
  "death": 4,
  "heroDamage": 4631,
  "cure": 6801,
  "resistDamage": 0,
  "rankInfo": {
    "rank_name": "Platinum",
    "rankName": "Platinum",
    "rank_sub_tier": 5,
    "rankSubTier": 5,
    "rankScore": 395,
    "ts": 1777212060658
  },
  "healingTaken": 2715.0,
  "damageTaken": 4966.0,
  "finalHit": 3,
  "targetCompetingTime": 9,
  "perks": [
    {
      "guid": "920986123797276132",
      "perkLevel": 1
    }
  ],
  "friendBnetIds": [],
  "beginTs": 1777212060658
}
```

Field notes:

- `name`: player display name
- `bnetId`: numeric Battle.net id
- `customerToken`: per-player customer token
- `heroGuid`: hero id
- `heroIcon`: hero icon URL
- basic combat stats: `kill`, `assist`, `death`, `heroDamage`, `cure`, `resistDamage`
- `rankInfo`: rank snapshot
- `healingTaken` / `damageTaken`: received stats
- `finalHit`: final blow count
- `targetCompetingTime`: objective / contest time
- `perks`: selected perks
- `friendBnetIds`: grouped queue friend ids if available

## Ban Hero Fields

Example:

```json
{
  "teamBanHeroGuids": [
    "207165582859043119",
    "207165582859043274"
  ],
  "enemyBanHeroGuids": [
    "207165582859044118",
    "207165582859043118"
  ]
}
```

These fields describe bans in match modes that support them.

## Raw Capture Mapping

The request in `672_Full.txt` is:

```text
GET /v1/a19ld5tool/customer/queryMatchInfo?matchId=<MATCH_ID>&season=&token=<CUSTOMER_TOKEN>
```

with Bigdata auth headers:

```text
GL-Bigdata-Auth-Token: <TOKEN>
GL-Bigdata-Dts: 2026
GL-Bigdata-Role-Id: <ROLE_ID>
GL-Bigdata-Server: 1
```

and returns a full normal-match detail payload.

## Notes

- This capture is the normal `customer/queryMatchInfo` endpoint, not the fight-mode `customer/fight/queryMatchInfo` variant.
- The payload is significantly larger than `queryMatchList` because it includes both teams and hero-level detail.
- Some player names in the capture appear garbled because the source text encoding is not fully normalized.
