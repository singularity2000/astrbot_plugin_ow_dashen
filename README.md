# astrbot_plugin_ow_dashen

守望先锋数据查询插件。你可以通过此插件查询：

- 玩家资料
- 最近战绩
- 单场对局详情
- 段位历史
- 快速强度 / 竞技强度
- 今日 / 昨日 / 本周总结
- 英雄热度榜单 / 单英雄历史曲线
- 商店
- 补丁说明

此插件由 <https://github.com/AddOneSecondL/Overstats> 移植而来（感谢原作者开源），已能正常使用，但由于工程量大，目前可能仍存在一些 bug。欢迎专业人士在使用中提交代码 PR 进行改进，精准重现原项目的数据返回体验。此插件现阶段着力于对原项目的功能进行完整移植，在插件 bug 完全修复、移植圆满完成之前，暂时谢绝超出原项目的个性化定制。

## 安装

在 AstrBot WebUI 中安装并启用插件。

## 使用前准备

这个插件必须先配置网易大神凭据，否则大部分玩家查询命令无法使用。

你至少需要准备：

1. 一个已绑定守望先锋战网账号的网易大神账号
2. 该账号对应的 `role_id`
3. 该账号对应的 `token`

`role_id` 和 `token` 的获取步骤如下。

### 获取 `role_id`

1. 登录网易大神官网：`https://ds.163.com`
2. 打开守望先锋相关页面或 **充值中心** ，确认已经绑定好战网账号
3. 按 `F12` 打开浏览器开发者工具
4. 切到 `Network` 标签页
5. 按 `Ctrl+F5` 强制刷新页面
6. 搜索 `role_id`
7. 复制属于你账号的数字值

### 获取 `token`

在网易大神官网按 `F12` 打开浏览器控制台，然后粘贴运行下面这段脚本。

把代码里的 `YOUR_ROLE_ID` 替换成你上一步拿到的 `role_id`。

```js
(async () => {
  const url = "https://inf.ds.163.com/v1/web/game/report/getReportToken";

  const payload = {
    appKey: "bn",
    roleId: "YOUR_ROLE_ID",
    server: "1",
    source: 1,
    type: "yearly",
  };

  function getCookie(name) {
    return (
      document.cookie
        .split("; ")
        .find((row) => row.startsWith(name + "="))
        ?.split("=")
        .slice(1)
        .join("=") || ""
    );
  }

  const body = JSON.stringify(payload);

  const sigMod = await window.sig.default();
  const signRaw = sigMod.gen_sign(body);
  const signObj = JSON.parse(signRaw);

  const xsrf = getCookie("GL-XSRF-TOKEN");
  const uid = getCookie("GOD_UUID");
  const deviceId =
    localStorage.getItem("ns-client-id") ||
    localStorage.getItem("ds-website-uuid") ||
    "";

  console.log("body =", body);
  console.log("GL-CheckSum =", signObj.sign);
  console.log("GL-Nonce =", signObj.timestamp);
  console.log("GL-X-XSRF-TOKEN =", xsrf);
  console.log("GL-Uid =", uid);
  console.log("GL-DeviceId =", deviceId);

  const resp = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json;charset=UTF-8",
      "GL-ClientType": "61",
      "GL-DeviceId": deviceId,
      "GL-Uid": uid,
      "GL-X-XSRF-TOKEN": xsrf,
      "GL-CheckSum": signObj.sign,
      "GL-Nonce": String(signObj.timestamp),
    },
    body,
  });

  const text = await resp.text();

  console.log("status =", resp.status);
  console.log("raw =", text);

  try {
    const json = JSON.parse(text);
    console.log("json =", json);
    console.log("role_id =", json?.result?.roleId || payload.roleId);
    console.log("token =", json?.result?.token || "");
  } catch (e) {
    console.log("not json");
  }
})();
```

如果请求成功，通常会得到类似这样的结果：

```json
{
  "result": {
    "appKey": "bn",
    "roleId": "123456789",
    "server": "1",
    "day": "2026",
    "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  },
  "code": 200,
  "errmsg": "OK"
}
```

其中：

- `result.roleId` 就是要填入插件配置的 `role_id`
- `result.token` 就是要填入插件配置的 `token`

## 配置

在 AstrBot WebUI 的插件配置页里，至少填好一组大神账号：

- `账号名称`
- `role_id`
- `token`
- `启用此账号`

建议第一次先只配 1 个账号，确认能用后再加备用号。

## 快速上手

推荐按这个顺序测试：

```text
/owhelp
/ow 绑定 <BattleTag>
/ow 我的绑定
/ow 资料
/ow 战绩
/ow 对局详情 1
/ow 段位
/ow 竞技强度 3
/ow 今日总结
/ow 商店
/ow 补丁
```

如果你已经绑定过 BattleTag，后续大部分命令都可以不再手动输入 BattleTag。

## 常用命令

### 帮助与绑定

```text
/owhelp
/ow 绑定 <BattleTag>
/ow 解绑
/ow 我的绑定
```

### 玩家查询

```text
/ow 资料 [BattleTag]
/ow 战绩 [BattleTag] [场数]
/ow 对局详情 [BattleTag] <序号>
/ow 段位 [BattleTag]
/ow 快速强度 [BattleTag] [场数]
/ow 竞技强度 [BattleTag] [场数]
/ow 今日总结 [BattleTag]
/ow 昨日总结 [BattleTag]
/ow 本周总结 [BattleTag]
```

### 英雄 / 商店 / 补丁

```text
/ow 英雄热度 [模式] [段位]
/ow 英雄曲线 <英雄名> [模式] [段位]
/ow 商店
/ow 补丁 [类型]
```

### 其他

```text
/ow 搜索玩家 <关键词>
/ow 自检
/ow 清理缓存
```

## 参数说明

### BattleTag

格式：

```text
名字#数字，例如 BattleTag#123456
```

### 场数

- `战绩`：建议 `1-20`
- `快速强度 / 竞技强度`：建议 `3-12`

### 模式

快速、竞技

### 段位

全部、青铜、白银、黄金、铂金、钻石、大师、宗师、冠军

### 补丁类型

最新、小更新、大更新

## 常见问题

### 1. 提示还没有绑定账号

先执行：

```text
/ow 绑定 你的BattleTag
```

### 2. 提示 BattleTag 格式不正确

请确认格式是：BattleTag#123456

### 3. 查询失败

先检查这几项：

1. `role_id` / `token` 是否有效
2. BattleTag 是否正确
3. 插件配置中的大神账号是否启用
4. 先试 `/ow 自检`

### 4. 某些命令比较慢

正常现象，尤其是：本周总结、强度分析、英雄曲线

这些命令请求更多上游数据，耗时会更长。

## 安全提醒

不要把 token 等涉及个人隐私的敏感信息发到公开仓库、公开群聊或 issue。

不要在与网易大神官方相关的平台上宣传此插件。

## 插件已知存在的问题（欢迎提出Issue、提交PR）

1. 插件长期运行由于产生图片缓存会导致体积膨胀。已有“ow 清理缓存”指令，但不能确定是否能完全清理掉临时数据。缓存保存的位置不够规范。
2. 部分命令，如“ow 英雄曲线 伊拉锐 快速 铂金”或“ow 本周总结”可能返回查询失败。

