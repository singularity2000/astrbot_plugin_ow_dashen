# queryCountInfo

This file documents the upstream Dashen competitive card / competitive summary endpoint captured in `423_Full.txt`.

Sensitive values in examples are masked:

- `GL-Bigdata-Auth-Token` -> `<TOKEN>`
- `GL-Bigdata-Role-Id` -> `<ROLE_ID>`
- `token` query param -> `<CUSTOMER_TOKEN>`
- `bnetId` -> `<BNET_ID>`
- `Cookie` / `GL-Uid` / `GL-DeviceId` / `traceId` -> `<MASKED>`

## Endpoint

`GET https://datamsapi.ds.163.com/v1/a19ld5tool/customer/queryCountInfo`

Current `overstats` client method:

- `DashenAPIClient.query_count_info(customer_token, game_mode, season=None)`

## Purpose

Query a player's competitive summary card and recent competitive stats.

For the captured request in `423_Full.txt`, the mode is:

- `gameMode=sport`

This upstream payload is one of the main data sources used by the profile module's competitive section.

## Request

### Query parameters

Masked example:

```text
gameMode=sport
season=
token=<CUSTOMER_TOKEN>
```

Field notes:

- `gameMode`: game mode, captured value is `sport`
- `season`: optional season number, empty in the capture means current season flow
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
    "guideCountData": [],
    "presetsSummaryData": {},
    "recentMatchCount": {},
    "matchList": [],
    "frequentHeroIds": [],
    "presetsHeroUseSummaryList": [],
    "openHeroUseSummaryList": [],
    "v6HeroUseSummaryList": [],
    "userProvinceRankList": [],
    "gameAction": {}
  },
  "success": true,
  "traceId": "<MASKED>"
}
```

### Important response fields

- `code == 0`: request succeeded
- `success == true`: request succeeded
- `data.bnetId`: numeric Battle.net id
- `data.guideCountData`: per-role competitive card data
- `data.presetsSummaryData`: overall competitive summary
- `data.recentMatchCount`: recent-match summary
- `data.matchList`: recent competitive matches
- `data.frequentHeroIds`: most used heroes
- `data.presetsHeroUseSummaryList`: hero usage summary for preset/competitive mode
- `data.userProvinceRankList`: province leaderboard info if available
- `data.gameAction`: social / commendation / report summary
- `traceId`: upstream trace id

## `guideCountData`

Example shape:

```json
[
  {
    "roleType": "healer",
    "lastRankInfo": {
      "rank_name": "Platinum",
      "rankName": "Platinum",
      "rank_sub_tier": 5,
      "rankSubTier": 5,
      "rankScore": 395,
      "ts": 1777212060658
    },
    "maxRankInfo": {
      "rank_name": "Platinum",
      "rankName": "Platinum",
      "rank_sub_tier": 5,
      "rankSubTier": 5,
      "rankScore": 395,
      "ts": 1777212060658
    },
    "matchSum": 67,
    "winRate": "64.18",
    "kda": "5.80",
    "coreCount": 10176,
    "maxWinStreak": 9
  }
]
```

Meaning:

- `roleType`: `tank` / `dps` / `healer`
- `lastRankInfo`: current rank snapshot
- `maxRankInfo`: peak rank snapshot
- `matchSum`: total matches for the role
- `winRate`: role win rate
- `kda`: role KDA
- `coreCount`: score / core metric from upstream
- `maxWinStreak`: maximum win streak

## `presetsSummaryData`

Example shape:

```json
{
  "matchSum": 104,
  "winRate": "59.62",
  "aveHeroDamage": 7023,
  "aveCure": 6965,
  "aveResistDamage": 4590,
  "aveKill": 14,
  "aveAssist": 12,
  "aveDeath": 5,
  "aveIndividualKill": 0,
  "aveFinalHit": 5,
  "matchWinSum": 62,
  "matchLossSum": 40,
  "serverMapCountData": {
    "death": 7.33,
    "damage": 8231.6,
    "cure": 3276.51,
    "resistDamage": 1264.47,
    "kill": 16.7,
    "maxDeath": 30,
    "maxDamage": 12000,
    "maxCure": 12000,
    "maxResistDamage": 12000,
    "maxKill": 20
  }
}
```

Meaning:

- overall competitive card summary
- averages are usually per match
- `serverMapCountData` is used for server-wide comparison / scale reference

## `recentMatchCount`

Example shape:

```json
{
  "aveDamage": 3634,
  "aveResistDamage": 106,
  "aveCure": 9329,
  "aveAssist": 14,
  "aveKill": 8,
  "winRate": "66.67",
  "roleType": "healer"
}
```

Meaning:

- summary of recent competitive matches
- often used as a "recent form" card block

## `matchList`

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
  "beginTs": 1777212060658,
  "gameMode": "SportPreset"
}
```

Meaning:

- recent competitive match list
- includes map, hero, role, combat stats, score, and rank snapshot

## `presetsHeroUseSummaryList`

This field is a large list of hero usage summary records. Each item typically contains:

- `heroGuid`
- `heroLevel`
- `matchSum`
- `winSum`
- `winRate`
- `gameTime`
- `statAveCount`
- `statPerTenMinCount`
- `heroRankInfo`

This section is usually the biggest part of the payload.

## Raw Capture Mapping

The request in `423_Full.txt` is:

```text
GET /v1/a19ld5tool/customer/queryCountInfo?gameMode=sport&season=&token=<CUSTOMER_TOKEN>
```

with Bigdata auth headers:

```text
GL-Bigdata-Auth-Token: <TOKEN>
GL-Bigdata-Dts: 2026
GL-Bigdata-Role-Id: <ROLE_ID>
GL-Bigdata-Server: 1
```

and returns a competitive summary payload with:

- role summaries
- overall summary
- recent match summary
- recent match list
- hero usage breakdown

## Notes

- Despite your description as "搜索玩家竞技卡片", the captured endpoint is technically `queryCountInfo`, not `queryCard`.
- `queryCard` is a separate upstream endpoint used for basic player card info.
- `423_Full.txt` is specifically the competitive-stat / competitive-card summary payload for `gameMode=sport`.
