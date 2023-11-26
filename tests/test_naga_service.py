import json
from pathlib import Path
from datetime import datetime

import pytest
from nonebug import App


@pytest.mark.asyncio
async def test_service(app: App):
    from nonebot_plugin_session import Session, SessionLevel

    from nonebot_plugin_nagabus.naga import naga
    from nonebot_plugin_nagabus.utils.tz import TZ_TOKYO
    from nonebot_plugin_nagabus.data.mjs import _set_get_majsoul_paipu_delegate

    async def get_majsoul_paipu(uuid):
        sample_path = str(Path(__file__).parent / "sample_majsoul_paipu.json")
        with open(sample_path, encoding="utf-8") as f:
            return json.load(f)

    _set_get_majsoul_paipu_delegate(get_majsoul_paipu)

    session = Session(
        bot_id="12345",
        bot_type="OneBot V11",
        platform="qq",
        level=SessionLevel.LEVEL2,
        id1="23456",
        id2="34567",
    )

    order = await naga.analyze_majsoul(
        "231126-23433728-1ce4-4a84-b945-7ab940d15d41", 0, 0, session
    )
    assert order.cost_np == 10

    order = await naga.analyze_tenhou("2023111804gm-0029-0000-1c8568b3", 0, session)
    assert order.cost_np == 50

    cur = datetime.now(tz=TZ_TOKYO)
    statistic = await naga.statistic(cur.year, cur.month)
    assert len(statistic) == 1
    assert statistic[0].cost_np == 60
