nonebot-plugin-nagabus
==========

NAGA公交车。为群友提供NAGA拼车服务。

## 用法

### 对于车主

首先你需要一个NAGA账号（废话），登录后在 https://naga.dmv.nico/naga_report/top/ 获取两个cookie（csrftoken和naga-report-session-id）填入配置中：

```
naga_cookies={"csrftoken":"xxxxxx","naga-report-session-id":"xxxxxx"}
```

其次你需要一个雀魂账号用于自动下载牌谱（推荐使用小号），将用户名与密码填入配置中：

```
majsoul_username=xxxxxx@xxx.com
majsoul_password=xxxxxx
```

还可以配置允许上车的群组、私聊：

```
naga_allow_private=[114514]
naga_allow_group=[1919810]
```

### 对于用户

- 牌谱解析：
    - /naga <雀魂牌谱链接> <东/南x局x本场>
- 查看使用情况：
    - /naga本月使用情况
    - /naga上月使用情况

以上命令格式中，以<>包裹的表示一个参数。
