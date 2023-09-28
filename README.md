nonebot-plugin-nagabus
==========

NAGA公交车。为群友提供NAGA拼车服务。

## 用法

### 对于车主

你需要一个雀魂账号用于自动下载牌谱（推荐使用小号），将用户名与密码填入配置中：

```
majsoul_username=xxxxxx@xxx.com
majsoul_password=xxxxxx
```

最后你需要一个NAGA账号（废话），登录后在 https://naga.dmv.nico/naga_report/top/ 获取两个cookie（csrftoken和naga-report-session-id），Bot启动后调用`/naga-set-cookies csrftoken=xxxxxxxx; naga-report-session-id=xxxxxxxx`指令

（指令仅超级用户可用，通过在配置文件中设置SUPERUSERS可设置超级用户）

```
SUPERUSERS=["12345678"]
```

#### 权限控制

配合[nonebot-plugin-access-control](https://github.com/ssttkkl/nonebot-plugin-access-control)，可以配置允许上车的群组和用户，或者是限制时间段内使用次数：

譬如，超级用户可以通过分别发送以下指令，从而只允许群聊114514使用。

```
/ac permission deny --srv nonebot_plugin_nagabus --sbj all
/ac permission allow --srv nonebot_plugin_nagabus --sbj qq:g114514
```

譬如，超级用户可以通过分别发送以下指令，从而限制每天只允许使用10次解析功能。（解析失败、重复解析不计算在内）

```
/ac limit add --srv nonebot_plugin_nagabus.analyze --sbj all --span 1d --limit 10
```

具体可以参考nonebot-plugin-access-control的文档进行权限控制。

### 对于用户

- 牌谱解析：
    - `/naga <雀魂牌谱链接> <东/南x局x本场>`：消耗10NP解析雀魂小局
    - `/naga <天凤牌谱链接>`：消耗50NP解析天凤半庄
- 查看使用情况：
    - `/naga本月使用情况`
    - `/naga上月使用情况`

以上命令格式中，以<>包裹的表示一个参数。

## Special Thanks

- https://github.com/Diving-Fish/auto-naga
