# from sr_mission import has_subtitles
# print(has_subtitles('/mnt/data/Video/结缘甘神神社/Season 1/结缘甘神神社 S01E01.mkv'))
# print(has_subtitles('/mnt/data/Downloads/[LoliHouse] Amagami-san Chi no Enmusubi - 01 [WebRip 1080p HEVC-10bit AAC SRTx2]).mkv'))

import asyncio

async def TASK_1():
    print("TASK_1")

async def TASK_2():
    print("TASK_2")
    task = asyncio.create_task(TASK_1())

loop = asyncio.get_event_loop()
loop.call_soon_threadsafe(asyncio.create_task, TASK_2())
loop.run_forever()