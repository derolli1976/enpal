"""Discover the correct SignalR hub method name for event dispatch on the Enpal Box.

Fetches the Blazor JavaScript from the Enpal Box and searches for
event-dispatch-related hub method names.
"""
import asyncio
import aiohttp
import re
import sys


async def main():
    base = 'http://192.168.2.70'

    async with aiohttp.ClientSession() as session:
        # 1. Fetch /wallbox HTML
        print(f"Fetching {base}/wallbox ...")
        async with session.get(f'{base}/wallbox') as resp:
            html = await resp.text()
        print(f"  HTML: {len(html)} bytes")

        # 2. Find Blazor script URLs
        script_srcs = re.findall(r'<script[^>]+src="([^"]*)"', html)
        print(f"  Script tags found: {script_srcs}")

        blazor_js_url = None
        for src in script_srcs:
            if 'blazor' in src.lower() or '_framework' in src.lower():
                blazor_js_url = src
                break

        # Also try common paths
        common_paths = [
            '/_framework/blazor.web.js',
            '/_framework/blazor.server.js',
            '/_content/Microsoft.AspNetCore.Components.Web/blazor.web.js',
        ]

        if blazor_js_url:
            # Make absolute
            if blazor_js_url.startswith('/'):
                blazor_js_url = base + blazor_js_url
            elif not blazor_js_url.startswith('http'):
                blazor_js_url = base + '/' + blazor_js_url

        print(f"\n  Primary Blazor JS URL: {blazor_js_url}")

        # 3. Fetch the Blazor JS (try primary + common paths)
        urls_to_try = []
        if blazor_js_url:
            urls_to_try.append(blazor_js_url)
        urls_to_try.extend([base + p for p in common_paths])

        js_code = None
        for url in urls_to_try:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        js_code = await resp.text()
                        print(f"\n  Found Blazor JS at: {url} ({len(js_code)} bytes)")
                        break
                    else:
                        print(f"  {url}: HTTP {resp.status}")
            except Exception as e:
                print(f"  {url}: {e}")

        if not js_code:
            print("\nERROR: Could not find Blazor JavaScript file!")
            return

        # 4. Search for event dispatch method names
        print(f"\n=== Searching for event dispatch methods ===")

        # Search for quoted strings that look like hub method names
        # In the minified JS, hub methods are typically quoted strings
        hub_methods = re.findall(r'"([A-Z][a-zA-Z]*(?:Event|Browser|Dispatch|Click|Mouse|Dom)[a-zA-Z]*)"', js_code)
        print(f"\n  Method-like strings with Event/Browser/Dispatch/Click/Mouse/Dom:")
        for m in sorted(set(hub_methods)):
            print(f"    {m}")

        # Also search for any string containing "dispatch" (case insensitive)
        dispatch_refs = re.findall(r'"([^"]{3,50}[Dd]ispatch[^"]{0,50})"', js_code)
        print(f"\n  Strings containing 'dispatch':")
        for m in sorted(set(dispatch_refs)):
            print(f"    {m}")

        # Search for known hub method names used in Blazor
        known_methods = [
            'StartCircuit', 'UpdateRootComponents', 'DispatchBrowserEvent',
            'DispatchEvent', 'BeginInvokeDotNetFromJS', 'EndInvokeJSFromDotNet',
            'OnRenderCompleted', 'OnLocationChanged', 'OnLocationChanging',
            'ReceiveByteArray', 'SendDotNetStreamAsync',
            'DispatchEventAsync', 'RaiseEvent', 'HandleEvent',
            'ReceiveEvent', 'ProcessEvent', 'SendEvent',
        ]
        print(f"\n  Known method name search:")
        for method in known_methods:
            count = js_code.count(f'"{method}"')
            if count > 0:
                # Show surrounding context
                idx = js_code.find(f'"{method}"')
                context_start = max(0, idx - 80)
                context_end = min(len(js_code), idx + len(method) + 82)
                context = js_code[context_start:context_end].replace('\n', ' ')
                print(f"    {method}: found {count}x")
                print(f"      context: ...{context}...")

        # Search for invoke/send patterns near "event" strings
        print(f"\n  Searching for .invoke/.send patterns near event handling:")
        for pattern in [
            r'\.invoke\s*\(\s*"([^"]+)"',
            r'\.send\s*\(\s*"([^"]+)"',
            r'connection\.invoke\s*\(\s*"([^"]+)"',
            r'\.invoke\("([^"]+)"',
            r'\.send\("([^"]+)"',
        ]:
            matches = re.findall(pattern, js_code)
            if matches:
                print(f"    Pattern '{pattern}':")
                for m in sorted(set(matches)):
                    print(f"      -> {m}")

        # Search specifically for event-related invocations
        print(f"\n  Broader search for hub invocations:")
        for pattern in [
            r'["\']([A-Z][a-zA-Z]{5,40})["\']',  # PascalCase strings 6-40 chars
        ]:
            matches = re.findall(pattern, js_code)
            # Filter to likely hub method names
            hub_like = [m for m in set(matches) if any(kw in m for kw in 
                        ['Dispatch', 'Event', 'Browser', 'Invoke', 'Render', 
                         'Circuit', 'Component', 'Location', 'Receive', 'Send',
                         'DotNet', 'ByteArray', 'Stream'])]
            if hub_like:
                for m in sorted(hub_like):
                    print(f"    {m}")

        # Save the JS file for manual inspection
        with open('scripts/blazor_js_dump.js', 'w', encoding='utf-8') as f:
            f.write(js_code)
        print(f"\n  Saved Blazor JS to scripts/blazor_js_dump.js for manual inspection")


if __name__ == '__main__':
    asyncio.run(main())
