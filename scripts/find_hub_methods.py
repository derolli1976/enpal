"""Fetch blazor.web.js from Enpal Box and extract hub method names."""
import asyncio
import aiohttp
import re


async def main():
    base = 'http://192.168.2.70'
    async with aiohttp.ClientSession() as session:
        url = f'{base}/_framework/blazor.web.js'
        print(f'Fetching {url}...')
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            print(f'Status: {resp.status}')
            if resp.status != 200:
                print('Failed!')
                return
            js = await resp.text()
            print(f'Size: {len(js)} bytes')

            with open('scripts/blazor_web_js.js', 'w', encoding='utf-8') as f:
                f.write(js)
            print('Saved to scripts/blazor_web_js.js')

        # Search for hub method names
        print('\n=== invoke() calls ===')
        for m in sorted(set(re.findall(r'\.invoke\("([^"]+)"', js))):
            print(f'  {m}')

        print('\n=== send() calls ===')
        for m in sorted(set(re.findall(r'\.send\("([^"]+)"', js))):
            print(f'  {m}')

        print('\n=== Strings containing Dispatch ===')
        for m in sorted(set(re.findall(r'"([^"]*[Dd]ispatch[^"]*)"', js))):
            if len(m) < 80:
                print(f'  {m}')

        print('\n=== Strings containing Event (PascalCase) ===')
        for m in sorted(set(re.findall(r'"([A-Z][a-zA-Z]*Event[a-zA-Z]*)"', js))):
            print(f'  {m}')

        print('\n=== All PascalCase strings that look like hub methods ===')
        keywords = ['Dispatch', 'Event', 'Browser', 'Invoke', 'Render',
                     'Circuit', 'Component', 'Location', 'Receive', 'DotNet',
                     'ByteArray', 'Stream', 'RootComponent']
        hub_like = set()
        for m in re.findall(r'"([A-Z][a-zA-Z]{5,50})"', js):
            if any(kw in m for kw in keywords):
                hub_like.add(m)
        for m in sorted(hub_like):
            # Show context
            idx = js.find(f'"{m}"')
            ctx_start = max(0, idx - 60)
            ctx_end = min(len(js), idx + len(m) + 62)
            ctx = js[ctx_start:ctx_end].replace('\n', ' ')
            print(f'  {m}')
            print(f'    ctx: ...{ctx}...')


if __name__ == '__main__':
    asyncio.run(main())
